from abc import ABCMeta, abstractmethod
from datetime import timedelta
from io import BufferedIOBase
import struct
from typing import Any, Union, Tuple, Optional

import msgpack  # type: ignore

from penguin_judge.models import JudgeStatus


class JudgeDriver(metaclass=ABCMeta):
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
