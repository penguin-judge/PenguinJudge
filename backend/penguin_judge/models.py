from contextlib import contextmanager
from enum import IntEnum
from typing import Iterator

from sqlalchemy import (
    Column, DateTime, Integer, String, LargeBinary, JSON, Enum,
    func)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

Base = declarative_base()
Session = scoped_session(sessionmaker())


class JudgeStatus(IntEnum):
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


class _JsonExportable(object):
    VALID_TYPES = (str, int, list, dict, float, bool)

    def to_dict(self) -> dict:
        keys = [
            k for k in dir(self)
            if (not k.startswith('_') and
                isinstance(getattr(self, k), self.VALID_TYPES))]
        return {k: getattr(self, k) for k in keys}

    def to_summary_dict(self) -> dict:
        if not hasattr(self, '__summary_keys__'):
            return self.to_dict()
        return {k: getattr(self, k) for k in getattr(self, '__summary_keys__')}


class User(Base, _JsonExportable):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    salt = Column(LargeBinary(32), nullable=False)
    password = Column(LargeBinary(32), nullable=False)
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)


class Environment(Base, _JsonExportable):
    __tablename__ = 'environments'
    __summary_keys__ = ['id', 'name']
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    config = Column(JSON)


class Contest(Base, _JsonExportable):
    __tablename__ = 'contests'
    __summary_keys__ = ['id', 'title']
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)


class Problem(Base, _JsonExportable):
    __tablename__ = 'problems'
    contest_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)


class TestCase(Base, _JsonExportable):
    __tablename__ = 'tests'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    input = Column(LargeBinary, nullable=False)
    output = Column(LargeBinary, nullable=False)


class Submission(Base, _JsonExportable):
    __tablename__ = 'submissions'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    code = Column(LargeBinary, nullable=False)
    environment_id = Column(Integer, nullable=False)
    status = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name,
        nullable=False)
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)


class JudgeResult(Base, _JsonExportable):
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
    drop_all = kwargs.pop('drop_all', None)
    if 'sqlalchemy.url' not in kwargs:
        kwargs['sqlalchemy.url'] = (
            'postgresql://ringo:ringo@localhost:5432/judge')
    engine = engine_from_config(kwargs)
    if drop_all:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session.configure(bind=engine)  # type: ignore


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
