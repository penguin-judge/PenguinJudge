from abc import ABC, abstractmethod
from datetime import timedelta
import os
from io import RawIOBase, BufferedIOBase, BufferedReader, BufferedWriter
from typing import Any, Union, Tuple, Optional, MutableSequence
import struct

import docker  # type: ignore
from zstandard import ZstdDecompressor  # type: ignore
import msgpack  # type: ignore

from penguin_judge.models import (
    JudgeStatus, Submission, JudgeResult, transaction, scoped_session)
from penguin_judge.check_result import equal_binary


class JudgeDriver(ABC):
    def prepare(self, task: dict) -> None:
        pass

    @abstractmethod
    def compile(self, task: dict) -> Union[JudgeStatus, Tuple[bytes, float]]:
        raise NotImplementedError

    @abstractmethod
    def tests(self, task: dict) -> Tuple[
            JudgeStatus, Optional[timedelta], Optional[int]]:
        raise NotImplementedError

    def __enter__(self) -> 'JudgeDriver':
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        pass

    def _send(self, strm: BufferedIOBase, obj: Any) -> None:
        b = msgpack.packb(obj, use_bin_type=True)
        strm.write(struct.pack('<I', len(b)))
        strm.write(b)
        strm.flush()

    def _recv(self, strm: BufferedIOBase) -> dict:
        sz = struct.unpack('<I', strm.read(4))[0]
        return msgpack.unpackb(strm.read(sz), raw=False)


class DockerJudgeDriver(JudgeDriver):
    def __init__(self) -> None:
        self.client = docker.APIClient()
        self.compile_container = None
        self.test_container = None
        self.time_limit = 0
        self.memory_limit = 0

    def prepare(self, task: dict) -> None:
        self.time_limit = task['problem']['time_limit']
        self.memory_limit = task['problem']['memory_limit']
        mem_limit = self.memory_limit * (2**20)
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
        if task['environment'].get('compile_image_name'):
            self.compile_container = self.client.create_container(
                task['environment'].get('compile_image_name'), **common_cfg)
            self.client.start(self.compile_container)
        self.test_container = self.client.create_container(
            task['environment']['test_image_name'], **common_cfg)
        self.client.start(self.test_container)

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        for c in (self.compile_container, self.test_container):
            if not c:
                continue
            try:
                self.client.kill(c)
            except Exception:
                pass

    def compile(self, task: dict) -> Union[JudgeStatus, Tuple[bytes, float]]:
        try:
            s = self.client.attach_socket(
                self.compile_container,
                params={'stdin': 1, 'stdout': 1, 'stream': 1})
            reader = BufferedReader(DockerStdoutReader(s))
            writer = BufferedWriter(DockerStdinWriter(s))
            # TODO(*): コンパイルのタイムアウト/メモリ上限はどうする?
            self._send(writer, {
                'type': 'Compilation',
                'code': task['code'],
                'time_limit': self.time_limit,
                'memory_limit': self.memory_limit,
            })
            resp = self._recv(reader)
            if isinstance(resp, dict) and resp.get('type') == 'Compilation':
                return (resp['binary'], resp['time'])
            return JudgeStatus.CompilationError
        except Exception:
            return JudgeStatus.InternalError

    def tests(self, task: dict) -> Tuple[
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
                    JudgeResult.contest_id == task['contest_id'],
                    JudgeResult.problem_id == task['problem_id'],
                    JudgeResult.submission_id == task['id'],
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
                'code': task['code'],
                'time_limit': self.time_limit,
                'memory_limit': self.memory_limit,
                'output_limit': 1,
            })

            status_set = set()
            for test in task['tests']:
                _update_status(test['id'], JudgeStatus.Running)
                self._send(writer, {
                    'type': 'Test',
                    'input': test['input']
                })
                resp = self._recv(reader)
                typ = resp.get('type')
                kind = resp.get('kind')
                if typ == 'Test':
                    assert isinstance(test['output'], bytes)
                    assert isinstance(resp['output'], bytes)
                    if equal_binary(test['output'], resp['output']):
                        status = JudgeStatus.Accepted
                    else:
                        status = JudgeStatus.WrongAnswer
                elif typ == 'Error' and isinstance(kind, str):
                    status = JudgeStatus.from_str(kind)
                time: Optional[timedelta] = None
                mem: Optional[int] = None
                time_raw, mem_raw = resp.get('time'), resp.get('memory_bytes')
                if time_raw is not None:
                    time = timedelta(seconds=time_raw)
                if mem_raw is not None:
                    mem = mem_raw // 1024
                _update_status(test['id'], status, time, mem)
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


def run(task: dict) -> JudgeStatus:
    print('judge start with below id')
    print('  contest_id: {}'.format(task['contest_id']))
    print('  problem_id: {}'.format(task['problem_id']))
    print('  submission_id: {}'.format(task['id']))
    print('  user_id: {}'.format(task['user_id']), flush=True)

    def update_submission_status(
            s: scoped_session, status: JudgeStatus) -> JudgeStatus:
        s.query(Submission).filter(
            Submission.contest_id == task['contest_id'],
            Submission.problem_id == task['problem_id'],
            Submission.id == task['id'],
        ).update({Submission.status: status}, synchronize_session=False)
        return status

    zctx = ZstdDecompressor()
    try:
        task['code'] = zctx.decompress(task['code'])
        for test in task['tests']:
            test['input'] = zctx.decompress(test['input'])
            test['output'] = zctx.decompress(test['output'])
    except Exception:
        with transaction() as s:
            return update_submission_status(s, JudgeStatus.InternalError)

    compile_time = None
    with DockerJudgeDriver() as judge:
        try:
            judge.prepare(task)
        except Exception:
            with transaction() as s:
                return update_submission_status(s, JudgeStatus.InternalError)
        if task['environment'].get('compile_image_name'):
            ret = judge.compile(task)
            if isinstance(ret, JudgeStatus):
                with transaction() as s:
                    update_submission_status(s, ret)
                    s.query(JudgeResult).filter(
                        JudgeResult.contest_id == task['contest_id'],
                        JudgeResult.problem_id == task['problem_id'],
                        JudgeResult.submission_id == task['id']
                    ).update({
                        JudgeResult.status: ret}, synchronize_session=False)
                print('judge failed: {}'.format(ret), flush=True)
                return ret
            task['code'], compile_time = ret[0], timedelta(seconds=ret[1])
        ret, max_time, max_memory = judge.tests(task)
        with transaction() as s:
            s.query(Submission).filter(
                Submission.contest_id == task['contest_id'],
                Submission.problem_id == task['problem_id'],
                Submission.id == task['id']
            ).update({
                Submission.status: ret,
                Submission.compile_time: compile_time,
                Submission.max_time: max_time,
                Submission.max_memory: max_memory,
            }, synchronize_session=False)
        print('judge finished: {}'.format(ret), flush=True)
        return ret
