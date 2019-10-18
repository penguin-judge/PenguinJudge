from contextlib import contextmanager
import datetime
import enum
from typing import Dict, Iterator, Optional, List

from sqlalchemy import (
    Column, DateTime, Integer, String, LargeBinary, JSON, Enum,
    func)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

Base = declarative_base()
Session = scoped_session(sessionmaker())
_config: Dict[str, str] = {}


class JudgeStatus(enum.Enum):
    Waiting = 0x00
    Running = 0x01
    Accepted = 0x10
    CompilationError = 0x20
    RuntimeError = 0x21
    WrongAnswer = 0x22
    MemoryLimitExceeded = 0x30
    TimeLimitExceeded = 0x31
    OutputLimitExceeded = 0x32
    InternalError = 0xFF


class _Exportable(object):
    VALID_TYPES = (
        str, int, list, dict, float, bool, bytes, datetime.datetime, enum.Enum)

    def to_dict(self, *, keys: Optional[List[str]] = None) -> dict:
        if not keys:
            keys = [
                k for k in dir(self)
                if (not k.startswith('_') and
                    isinstance(getattr(self, k), self.VALID_TYPES))]
        return {k: getattr(self, k) for k in keys}

    def to_summary_dict(self) -> dict:
        return self.to_dict(keys=getattr(self, '__summary_keys__', None))


class User(Base, _Exportable):
    __tablename__ = 'users'
    __summary_keys__ = ['name', 'created']
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    salt = Column(LargeBinary(32), nullable=False)
    password = Column(LargeBinary(32), nullable=False)
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)


class Environment(Base, _Exportable):
    __tablename__ = 'environments'
    __summary_keys__ = ['id', 'name']
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    config = Column(JSON)


class Contest(Base, _Exportable):
    __tablename__ = 'contests'
    __summary_keys__ = ['id', 'title', 'start_time', 'end_time']
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)


class Problem(Base, _Exportable):
    __tablename__ = 'problems'
    contest_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    time_limit = Column(Integer, nullable=False)
    memory_limit = Column(Integer, nullable=False)
    description = Column(String, nullable=False)


class TestCase(Base, _Exportable):
    __tablename__ = 'tests'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    input = Column(LargeBinary, nullable=False)
    output = Column(LargeBinary, nullable=False)


class Submission(Base, _Exportable):
    __tablename__ = 'submissions'
    __summary_keys__ = ['contest_id', 'problem_id', 'id', 'user_id',
                        'environment_id', 'status', 'created']
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    code = Column(LargeBinary, nullable=False)
    environment_id = Column(Integer, nullable=False)
    status = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name,
        nullable=False)
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)


class JudgeResult(Base, _Exportable):
    __tablename__ = 'judge_results'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    submission_id = Column(Integer, primary_key=True)
    test_id = Column(String, primary_key=True)
    status = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name,
        nullable=False)


def configure(**kwargs: str) -> None:
    from sqlalchemy import engine_from_config
    global _config
    drop_all = kwargs.pop('drop_all', None)
    _config = {k: v for k, v in kwargs.items() if k.startswith('sqlalchemy.')}
    engine = engine_from_config(kwargs)
    if drop_all:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session.configure(bind=engine)  # type: ignore


def get_db_config() -> Dict[str, str]:
    return _config


@contextmanager
def transaction() -> Iterator[scoped_session]:
    try:
        yield Session
        Session.commit()
    except Exception:
        Session.rollback()
        raise
    finally:
        Session.remove()
