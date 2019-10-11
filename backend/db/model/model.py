from enum import IntEnum
from sqlalchemy import (
    Column, DateTime, Integer, String, LargeBinary, JSON, Enum,
    func)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager
from typing import Iterator

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

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    salt = Column(LargeBinary(32), nullable=False)
    password = Column(LargeBinary(32), nullable=False)
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

class Contest(Base):
    __tablename__ = 'contests'
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    start_time = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

class Environment(Base):
    __tablename__ = 'environments'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    config = Column(JSON)

class Problem(Base):
    __tablename__ = 'problems'
    id = Column(String, primary_key=True)
    contest_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)

class TestCase(Base):
    __tablename__ = 'tests'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    input = Column(LargeBinary, nullable=False)
    output = Column(LargeBinary, nullable=False)

class Submission(Base):
    __tablename__ = 'submissions'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    id = Column(Integer, primary_key=True)
    user_id = Column(String, primary_key=True)
    code = Column(LargeBinary, nullable=False)
    environment_id = Column(Integer, nullable=False)
    status = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name,
        nullable=False)
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

class JudgeResult(Base):
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
            'postgresql://kaming:kaming@localhost:5432/judge')
    engine = engine_from_config(kwargs)
    if drop_all:
        Base.metadata.drop_all(engine)
    else:
        Base.metadata.create_all(engine)
    Session.configure(bind=engine)

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