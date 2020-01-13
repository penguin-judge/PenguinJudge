from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from io import BufferedIOBase
import struct
from typing import (
    Any, Callable, Union, Optional, List, NamedTuple, Type, TypeVar)

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
    compile_time: Optional[timedelta] = None


class AgentCompilationResult(NamedTuple):
    binary: bytes
    time: float


class AgentTestResult(NamedTuple):
    output: bytes
    time: float
    memory_bytes: int


class AgentError(NamedTuple):
    kind: str


T = TypeVar('T')
TStartTestCallback = Callable[[str], None]
TJudgeCallback = Callable[
    [JudgeTestInfo, Union[AgentTestResult, AgentError]], None]
CompileResult = AgentCompilationResult


class JudgeDriver(metaclass=ABCMeta):
    def prepare(self, task: JudgeTask) -> None:
        pass

    @abstractmethod
    def compile(self, task: JudgeTask) -> Union[JudgeStatus, CompileResult]:
        raise NotImplementedError

    @abstractmethod
    def tests(self, task: JudgeTask,
              start_test_callback: TStartTestCallback,
              judge_complete_callback: TJudgeCallback) -> None:
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

    def __recv(self, strm: BufferedIOBase) -> dict:
        sz = struct.unpack('<I', strm.read(4))[0]
        return msgpack.unpackb(strm.read(sz), raw=False)

    def __recv_agent_resp(
            self, strm: BufferedIOBase, cls: Type[T]) -> Union[T, AgentError]:
        o = self.__recv(strm)
        if not isinstance(o, dict) or 'type' not in o:
            raise ValueError('invalid agent response')
        if o['type'] == 'Error':
            return AgentError(kind=o['kind'])
        args = [o[n] for n in cls._fields]  # type: ignore
        return cls(*args)

    def _recv_compile_result(self, strm: BufferedIOBase) -> Union[
            AgentCompilationResult, AgentError]:
        return self.__recv_agent_resp(strm, AgentCompilationResult)

    def _recv_test_result(self, strm: BufferedIOBase) -> Union[
            AgentTestResult, AgentError]:
        return self.__recv_agent_resp(strm, AgentTestResult)
