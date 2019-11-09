from contextlib import contextmanager
import datetime
import enum
from typing import Dict, Iterator, Optional, List

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, LargeBinary, Interval, Enum,
    func, ForeignKeyConstraint, Index)
from sqlalchemy.exc import IntegrityError, ProgrammingError
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

    @staticmethod
    def from_str(s: str) -> 'JudgeStatus':
        s = s.lower()
        for item in JudgeStatus:
            if item.name.lower() == s:
                return item
        raise RuntimeError


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
    __summary_keys__ = ['id', 'name', 'created', 'admin']
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    salt = Column(LargeBinary(32), nullable=False)
    password = Column(LargeBinary(32), nullable=False)
    admin = Column(Boolean, server_default='False')
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)


class Token(Base, _Exportable):
    __tablename__ = 'tokens'
    token = Column(LargeBinary(32), primary_key=True)
    user_id = Column(String, nullable=False)
    expires = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint([user_id], [User.id]),  # type: ignore
    )


class Environment(Base, _Exportable):
    __tablename__ = 'environments'
    __summary_keys__ = ['id', 'name']
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    compile_image_name = Column(String, nullable=True)
    test_image_name = Column(String)


class Contest(Base, _Exportable):
    __tablename__ = 'contests'
    __updatable_keys__ = [
        'title', 'description', 'start_time', 'end_time', 'published']
    __summary_keys__ = ['id', 'title', 'start_time', 'end_time', 'published']
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    published = Column(Boolean, server_default='False', nullable=False)
    penalty = Column(Interval, server_default='300', nullable=False)

    def is_begun(self) -> bool:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        return self.start_time <= now

    def is_finished(self) -> bool:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        return self.end_time <= now

    def is_accessible(self, user_info: Optional[dict]) -> bool:
        return self.published or (  # type: ignore
            user_info is not None and user_info['admin'])


class Problem(Base, _Exportable):
    __tablename__ = 'problems'
    __updatable_keys__ = [
        'title', 'description', 'time_limit', 'memory_limit', 'score']
    contest_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    time_limit = Column(Integer, nullable=False)
    memory_limit = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint([contest_id], [Contest.id]),  # type: ignore
    )


class TestCase(Base, _Exportable):
    __tablename__ = 'tests'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    input = Column(LargeBinary, nullable=False)
    output = Column(LargeBinary, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint([contest_id, problem_id],  # type: ignore
                             [Problem.contest_id, Problem.id]),
    )


class Submission(Base, _Exportable):
    __tablename__ = 'submissions'
    __summary_keys__ = ['contest_id', 'problem_id', 'id', 'user_id',
                        'environment_id', 'status', 'created']
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(String, nullable=False)
    problem_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    code = Column(LargeBinary, nullable=False)
    environment_id = Column(Integer, nullable=False)
    status = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name,
        nullable=False)
    compile_time = Column(Interval, nullable=True)
    created = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            [contest_id, problem_id],  # type: ignore
            [Problem.contest_id, Problem.id]),
        ForeignKeyConstraint(
            [user_id], [User.id]),  # type: ignore
        ForeignKeyConstraint(
            [environment_id], [Environment.id]),  # type: ignore
        Index('submissions_contest_problem_idx', contest_id, problem_id),
    )


class JudgeResult(Base, _Exportable):
    __tablename__ = 'judge_results'
    contest_id = Column(String, primary_key=True)
    problem_id = Column(String, primary_key=True)
    submission_id = Column(Integer, primary_key=True)
    test_id = Column(String, primary_key=True)
    status = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name,
        nullable=False)
    time = Column(Interval, nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(
            [submission_id],  # type: ignore
            [Submission.id]),
        ForeignKeyConstraint(
            [contest_id, problem_id, test_id],  # type: ignore
            [TestCase.contest_id, TestCase.problem_id, TestCase.id]),
    )


def configure(**kwargs: str) -> None:
    from sqlalchemy import engine_from_config
    global _config
    drop_all = kwargs.pop('drop_all', None)
    _config = {k: v for k, v in kwargs.items() if k.startswith('sqlalchemy.')}
    engine = engine_from_config(kwargs)
    if drop_all:
        Base.metadata.drop_all(engine)
    while True:
        try:
            Base.metadata.create_all(engine)
            break
        except (IntegrityError, ProgrammingError):
            # 同時起動した別プロセスがテーブル作成中なのでリトライ
            import time
            import random
            time.sleep(random.uniform(0.05, 0.1))
    Session.configure(bind=engine)  # type: ignore
    _insert_debug_data()  # デバッグ用に初期データを投入


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


def _insert_debug_data() -> None:
    import datetime
    from typing import Any
    from zstandard import ZstdCompressor  # type: ignore
    from penguin_judge.api import _kdf

    def _add(o: Any) -> None:
        try:
            with transaction() as s:
                if isinstance(o, Environment):
                    if s.query(Environment).filter(
                            Environment.name == o.name).first():
                        return
                s.add(o)
        except Exception:
            pass

    ctx = ZstdCompressor()

    salt = b'penguin'
    passwd = _kdf('penguinpenguin', salt)
    _add(User(
        id='admin', name='Administrator', salt=salt, admin=True,
        password=passwd))
    _add(Environment(
        name="C (gcc 8.2)",
        compile_image_name="penguin_judge_c_compile:8.2",
        test_image_name="penguin_judge_c_judge:8.2"))
    _add(Environment(
        name="Python3 (3.8.0)",
        test_image_name="penguin_judge_python:3.8"))
    _add(Contest(
        id="abc000",
        title="ABC000",
        description="# Title\nMarkdown Test\n\n* Item0\n* Item1\n",
        published=True,
        start_time=datetime.datetime.now(tz=datetime.timezone.utc),
        end_time=datetime.datetime.now(
            tz=datetime.timezone.utc) + datetime.timedelta(days=365)))
    _add(Problem(
        contest_id="abc000",
        id="A",
        title="Increment",
        description="# Increment\n\n標準入力から与えられた整数を1インクリメントした値を出力する",
        time_limit=1,
        memory_limit=1024,
        score=100))
    _add(TestCase(
        contest_id="abc000",
        problem_id="A",
        id="1",
        input=ctx.compress(b'1\n'),
        output=ctx.compress(b'2\n')))
    _add(TestCase(
        contest_id="abc000",
        problem_id="A",
        id="100",
        input=ctx.compress(b'100\n'),
        output=ctx.compress(b'101\n')))
