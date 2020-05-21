import os
from io import RawIOBase, BufferedReader, BufferedWriter
from typing import Any, Union, MutableSequence
import struct
from logging import getLogger

import docker  # type: ignore

from penguin_judge.models import JudgeStatus
from penguin_judge.judge import (
    JudgeDriver, JudgeTask, TStartTestCallback, TJudgeCallback,
    AgentCompilationResult, CompileResult)

LOGGER = getLogger(__name__)


class DockerJudgeDriver(JudgeDriver):
    def __init__(self) -> None:
        self.client = docker.APIClient()
        self.compile_container = None
        self.test_container = None

    def prepare(self, task: JudgeTask) -> None:
        mem_limit = task.memory_limit * (2**20)
        common_host_cfg = dict(
            auto_remove=True,
            cap_drop=['ALL'])
        common_cfg = dict(
            stdin_open=True,
            network_disabled=True,
        )
        if task.compile_image_name:
            compile_cfg = dict(
                host_config=self.client.create_host_config(**dict(
                    mem_limit=2**30,  # TODO(*): 1GB上限
                    memswap_limit=2**30,  # TODO(*): 1GB上限
                    **common_host_cfg)),
                **common_cfg,
            )
            self.compile_container = self.client.create_container(
                task.compile_image_name, **compile_cfg)
            self.client.start(self.compile_container)

        # pids_limit:
        #    go-langは7, nodejsは8, jdk14は17程度, それ以外は3が最低限。
        #    余裕を見て20を指定しておく
        test_cfg = dict(
            host_config=self.client.create_host_config(**dict(
                mem_limit=mem_limit,
                memswap_limit=mem_limit,
                pids_limit=20,
                **common_host_cfg)),
            **common_cfg,
        )
        self.test_container = self.client.create_container(
            task.test_image_name, **test_cfg)
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

    def tests(self, task: JudgeTask,
              start_test_callback: TStartTestCallback,
              judge_complete_callback: TJudgeCallback) -> None:
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
            'output_limit': 16,  # TODO(*): ハードコードじゃなく制御できるようにする
        })
        for test in task.tests:
            start_test_callback(test.id)
            self._send(writer, {
                'type': 'Test',
                'input': test.input
            })
            resp = self._recv_test_result(reader)
            judge_complete_callback(test, resp)


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
