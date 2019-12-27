from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from io import BufferedIOBase
import struct
from typing import Any, Union, Tuple, Optional, List, NamedTuple

import msgpack  # type: ignore

from penguin_judge.models import JudgeStatus


@dataclass
class JudgeTestInfo(object):
    id: str
    input: bytes
    output: bytes


@dataclass
class JudgeTask(object):
    id: int
    contest_id: str
    problem_id: str
    user_id: str
    code: bytes
    compile_image_name: Optional[str]
    test_image_name: str
    time_limit: int
    memory_limit: int
    tests: List[JudgeTestInfo]


class CompileResult(NamedTuple):
    binary: bytes
    time: float


class JudgeDriver(metaclass=ABCMeta):
    def prepare(self, task: JudgeTask) -> None:
        pass

    @abstractmethod
    def compile(self, task: JudgeTask) -> Union[JudgeStatus, CompileResult]:
        raise NotImplementedError

    @abstractmethod
    def tests(self, task: JudgeTask) -> Tuple[
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
