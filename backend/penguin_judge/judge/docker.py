from datetime import timedelta
import os
from io import RawIOBase, BufferedReader, BufferedWriter
from typing import Any, Union, Tuple, Optional, MutableSequence
import struct
from logging import getLogger

import docker  # type: ignore

from penguin_judge.models import JudgeStatus, JudgeResult, transaction
from penguin_judge.check_result import equal_binary
from penguin_judge.judge import (
    JudgeDriver, JudgeTask,
    AgentCompilationResult, AgentTestResult, CompileResult)

LOGGER = getLogger(__name__)


class DockerJudgeDriver(JudgeDriver):
    def __init__(self) -> None:
        self.client = docker.APIClient()
        self.compile_container = None
        self.test_container = None

    def prepare(self, task: JudgeTask) -> None:
        mem_limit = task.memory_limit * (2**20)
        common_cfg = dict(
            stdin_open=True,
            network_disabled=True,
            host_config=self.client.create_host_config(
                auto_remove=True,
                cap_drop=['ALL'],
                mem_limit=mem_limit,
                memswap_limit=mem_limit,
            ),
        )
        if task.compile_image_name:
            # TODO(*): 冗長なのを見直す
            compile_cfg = dict(
                stdin_open=True,
                network_disabled=True,
                host_config=self.client.create_host_config(
                    auto_remove=True,
                    cap_drop=['ALL'],
                    mem_limit=2**30,  # TODO(*): 1GB上限
                    memswap_limit=2**30,  # TODO(*): 1GB上限
                ),
            )
            self.compile_container = self.client.create_container(
                task.compile_image_name, **compile_cfg)
            self.client.start(self.compile_container)
        self.test_container = self.client.create_container(
            task.test_image_name, **common_cfg)
        self.client.start(self.test_container)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        for c in (self.compile_container, self.test_container):
            if not c:
                continue
            try:
                self.client.kill(c)
            except Exception:
                pass

    def compile(self, task: JudgeTask) -> Union[JudgeStatus, CompileResult]:
        try:
            s = self.client.attach_socket(
                self.compile_container,
                params={'stdin': 1, 'stdout': 1, 'stream': 1})
            reader = BufferedReader(DockerStdoutReader(s))
            writer = BufferedWriter(DockerStdinWriter(s))
            self._send(writer, {
                'type': 'Compilation',
                'code': task.code,
                'time_limit': 60,  # TODO(*): コンパイル時間の上限をえいやで1分に
                'memory_limit': 1024,  # TODO(*): 1GB上限(docker側の制限とあわせる)
            })
            resp = self._recv_compile_result(reader)
            if isinstance(resp, AgentCompilationResult):
                return resp
            return JudgeStatus.CompilationError
        except Exception:
            return JudgeStatus.InternalError

    def tests(self, task: JudgeTask) -> Tuple[
            JudgeStatus, Optional[timedelta], Optional[int]]:
        max_time: Optional[timedelta] = None
        max_memory: Optional[int] = None

        def _update_status(test_id: str, st: JudgeStatus,
                           time: Optional[timedelta] = None,
                           memory_kb: Optional[int] = None) -> None:
            updates: dict = {JudgeResult.status: st}
            if time is not None:
                updates[JudgeResult.time] = time
            if memory_kb is not None:
                updates[JudgeResult.memory] = memory_kb
            with transaction() as s:
                s.query(JudgeResult).filter(
                    JudgeResult.contest_id == task.contest_id,
                    JudgeResult.problem_id == task.problem_id,
                    JudgeResult.submission_id == task.id,
                    JudgeResult.test_id == test_id,
                ).update(updates, synchronize_session=False)

        try:
            s = self.client.attach_socket(
                self.test_container,
                params={'stdin': 1, 'stdout': 1, 'stream': 1})
            reader = BufferedReader(DockerStdoutReader(s))
            writer = BufferedWriter(DockerStdinWriter(s))
            self._send(writer, {
                'type': 'Preparation',
                'code': task.code,
                'time_limit': task.time_limit,
                'memory_limit': task.memory_limit,
                'output_limit': 1,
            })

            status_set = set()
            for test in task.tests:
                _update_status(test.id, JudgeStatus.Running)
                self._send(writer, {
                    'type': 'Test',
                    'input': test.input
                })
                resp = self._recv_test_result(reader)
                time_raw: Optional[float] = None
                mem_raw: Optional[int] = None
                if isinstance(resp, AgentTestResult):
                    time_raw, mem_raw = resp.time, resp.memory_bytes
                    if equal_binary(test.output, resp.output):
                        status = JudgeStatus.Accepted
                    else:
                        status = JudgeStatus.WrongAnswer
                else:
                    status = JudgeStatus.from_str(resp.kind)
                time: Optional[timedelta] = None
                mem: Optional[int] = None
                if time_raw is not None:
                    time = timedelta(seconds=time_raw)
                if mem_raw is not None:
                    mem = mem_raw // 1024
                _update_status(test.id, status, time, mem)
                if time is not None and (max_time is None or max_time < time):
                    max_time = time
                if mem is not None and (
                        max_memory is None or max_memory < mem):
                    max_memory = mem
                status_set.add(status)

            if len(status_set) == 1:
                return list(status_set)[0], max_time, max_memory
            for x in (JudgeStatus.InternalError, JudgeStatus.RuntimeError,
                      JudgeStatus.WrongAnswer, JudgeStatus.MemoryLimitExceeded,
                      JudgeStatus.TimeLimitExceeded,
                      JudgeStatus.OutputLimitExceeded):
                if x in status_set:
                    return x, max_time, max_memory
            raise RuntimeError  # 未知のkindの場合はInternalError
        except Exception:
            return JudgeStatus.InternalError, max_time, max_memory


class DockerStdoutReader(RawIOBase):
    def __init__(self, raw: RawIOBase) -> None:
        self._raw = BufferedReader(raw)
        self._cur = b''
        self._eos = False

    def readable(self) -> bool:
        return True

    def readinto(self, b: MutableSequence[int]) -> int:
        if not self._cur:
            self._read_next_frame()
        if self._eos or not self._cur:
            return -1
        sz = min(len(b), len(self._cur))
        b[0:sz] = self._cur[0:sz]
        self._cur = self._cur[sz:]
        return sz

    def _read_next_frame(self) -> None:
        while True:
            header = self._raw.read(8)
            if not header:
                self._eos = True
                return
            if len(header) != 8:
                raise IOError
            sz = struct.unpack('>I', header[4:])[0]
            body = self._raw.read(sz)
            if header[0] == 0x01:
                self._cur = body
                return


class DockerStdinWriter(RawIOBase):
    def __init__(self, raw: RawIOBase) -> None:
        self._fd = raw.fileno()

    def writable(self) -> bool:
        return True

    def write(self, b: bytes) -> int:
        return os.write(self._fd, b)
