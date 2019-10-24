from abc import ABC, abstractmethod
import os
from io import RawIOBase
from typing import Any, Union
import struct

import docker  # type: ignore
from zstandard import ZstdDecompressor  # type: ignore
import msgpack  # type: ignore

from penguin_judge.models import (
    JudgeStatus, Submission, JudgeResult, transaction)
from penguin_judge.check_result import equal_binary


class JudgeDriver(ABC):
    @abstractmethod
    def compile(self, task: dict) -> Union[JudgeStatus, bytes]:
        raise NotImplementedError

    @abstractmethod
    def tests(self, task: dict) -> JudgeStatus:
        raise NotImplementedError

    def _send(self, strm: RawIOBase, obj: Any) -> None:
        b = msgpack.packb(obj, use_bin_type=True)
        fd = strm.fileno()

        def _write_all(x: bytes) -> None:
            off = 0
            while off < len(x):
                ret = os.write(fd, x[off:])
                if not ret:
                    raise IOError
                off += ret
        _write_all(struct.pack('<I', len(b)))
        _write_all(b)

    def _recv(self, strm: RawIOBase) -> dict:
        def _read_exact(sz: int) -> bytearray:
            off, buf = 0, memoryview(bytearray(sz))
            while off < sz:
                ret = strm.readinto(buf[off:])  # type: ignore
                if not ret:
                    raise IOError
                off += ret
            return buf.obj  # type: ignore

        _read_exact(8)  # 何故か8バイトゴミが入ってる...
        sz = struct.unpack('<I', _read_exact(4))[0]
        return msgpack.unpackb(_read_exact(sz), raw=False)


class DockerJudgeDriver(JudgeDriver):
    def __init__(self) -> None:
        self.client = docker.APIClient()

    def compile(self, task: dict) -> Union[JudgeStatus, bytes]:
        compile_image_name = task['environment']['compile_image_name']
        container = self.client.create_container(
            compile_image_name, stdin_open=True)
        try:
            self.client.start(container)
            s = self.client.attach_socket(
                container, params={'stdin': 1, 'stdout': 1, 'stream': 1})
            self._send(s, {
                'type': 'Compilation',
                'code': task['code'],
                'time_limit': 10,
                'memory_limit': 10,
            })
            resp = self._recv(s)
            if isinstance(resp, dict) and resp.get('type') == 'Compilation':
                return resp['binary']
            return JudgeStatus.CompilationError
        except Exception:
            return JudgeStatus.InternalError
        finally:
            self.client.stop(container)
            self.client.remove_container(container)

    def tests(self, task: dict) -> JudgeStatus:
        test_image_name = task['environment']['test_image_name']
        container = self.client.create_container(
            test_image_name, stdin_open=True)

        def _update_status(test_id: str, st: JudgeStatus) -> None:
            with transaction() as s:
                s.query(JudgeResult).filter(
                    JudgeResult.contest_id == task['contest_id'],
                    JudgeResult.problem_id == task['problem_id'],
                    JudgeResult.submission_id == task['id'],
                    JudgeResult.test_id == test_id,
                ).update({JudgeResult.status: st}, synchronize_session=False)

        try:
            self.client.start(container)
            s = self.client.attach_socket(
                container, params={'stdin': 1, 'stdout': 1, 'stream': 1})
            self._send(s, {
                'type': 'Preparation',
                'code': task['code'],
                'time_limit': 10,
                'memory_limit': 10,
            })

            status_set = set()
            for test in task['tests']:
                _update_status(test['id'], JudgeStatus.Running)
                self._send(s, {
                    'type': 'Test',
                    'input': test['input']
                })
                resp = self._recv(s)
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
                _update_status(test['id'], status)
                status_set.add(status)

            if len(status_set) == 1:
                return list(status_set)[0]
            for x in (JudgeStatus.InternalError, JudgeStatus.RuntimeError,
                      JudgeStatus.WrongAnswer, JudgeStatus.MemoryLimitExceeded,
                      JudgeStatus.TimeLimitExceeded,
                      JudgeStatus.OutputLimitExceeded):
                if x in status_set:
                    return x
            raise RuntimeError  # 未知のkindの場合はInternalError
        except Exception:
            return JudgeStatus.InternalError
        finally:
            self.client.stop(container)
            self.client.remove_container(container)


def run(task: dict) -> None:
    try:
        _run(task)
    except Exception as e:
        print(e, flush=True)
        raise


def _run(task: dict) -> None:
    print('judge start with below id')
    print('  contest_id: {}'.format(task['contest_id']))
    print('  problem_id: {}'.format(task['problem_id']))
    print('  submission_id: {}'.format(task['id']))
    print('  user_id: {}'.format(task['user_id']), flush=True)

    zctx = ZstdDecompressor()
    task['code'] = zctx.decompress(task['code'])
    for test in task['tests']:
        test['input'] = zctx.decompress(test['input'])
        test['output'] = zctx.decompress(test['output'])

    judge = DockerJudgeDriver()
    if task['environment'].get('compile_image_name'):
        ret = judge.compile(task)
        if isinstance(ret, bytes):
            task['code'] = ret
        else:
            with transaction() as s:
                s.query(Submission).filter(
                    Submission.contest_id == task['contest_id'],
                    Submission.problem_id == task['problem_id'],
                    Submission.id == task['id']
                ).update({Submission.status: ret}, synchronize_session=False)
                s.query(JudgeResult).filter(
                    JudgeResult.contest_id == task['contest_id'],
                    JudgeResult.problem_id == task['problem_id'],
                    JudgeResult.submission_id == task['id']
                ).update({Submission.status: ret}, synchronize_session=False)
            print('judge failed: {}'.format(ret), flush=True)
            return

    ret = judge.tests(task)
    with transaction() as s:
        s.query(Submission).filter(
            Submission.contest_id == task['contest_id'],
            Submission.problem_id == task['problem_id'],
            Submission.id == task['id']
        ).update({Submission.status: ret}, synchronize_session=False)
    print('judge finished: {}'.format(ret), flush=True)
