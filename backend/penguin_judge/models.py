import datetime
import enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    Interval,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.orm import declarative_base

from penguin_judge.utils import to_fastapi_response_compatible_value

if TYPE_CHECKING:
    from penguin_judge.api.auth import Claims

Base = declarative_base()
_config: Dict[str, str] = {}


class JudgeStatus(enum.IntEnum):
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
    def from_str(s: str) -> "JudgeStatus":
        s = s.lower()
        for item in JudgeStatus:
            if item.name.lower() == s:
                return item
        raise RuntimeError


class _Exportable(object):
    VALID_TYPES = (
        str,
        int,
        list,
        dict,
        float,
        bool,
        bytes,
        datetime.datetime,
        datetime.timedelta,
        enum.Enum,
    )

    def to_dict(
        self, *, keys: Optional[List[str]] = None
    ) -> dict[str, str | bool | int | float | None]:
        if not keys:
            keys = [k for k in dir(self) if not k.startswith("_")]

        return {
            k: to_fastapi_response_compatible_value(getattr(self, k))
            for k in keys
            if isinstance(getattr(self, k), self.VALID_TYPES)
        }

    def to_summary_dict(self) -> dict[str, str | bool | int | float | None]:
        return self.to_dict(keys=getattr(self, "__summary_keys__", None))


class User(Base, _Exportable):
    __tablename__ = "users"
    __summary_keys__ = ["id", "name", "created", "admin"]
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    login_id: str = Column(String, nullable=False, unique=True)
    name: str = Column(String, nullable=False, unique=True)
    salt: bytes = Column(LargeBinary(32), nullable=False)
    password: bytes = Column(LargeBinary(32), nullable=False)
    admin: bool = Column(Boolean, server_default="False")
    created: datetime.datetime = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Token(Base, _Exportable):
    __tablename__ = "tokens"
    token: bytes = Column(LargeBinary(32), primary_key=True)
    user_id: int = Column(Integer, nullable=False)
    expires: datetime.datetime = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (ForeignKeyConstraint([user_id], [User.id]),)  # type: ignore


class Environment(Base, _Exportable):
    __tablename__ = "environments"
    __summary_keys__ = ["id", "name", "active"]
    __updatable_keys__ = [
        "name",
        "active",
        "published",
        "compile_image_name",
        "test_image_name",
    ]
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String, nullable=False)
    active: bool = Column(Boolean, server_default="True")
    published: bool = Column(Boolean, server_default="False")
    compile_image_name: str | None = Column(String, nullable=True)
    test_image_name: str = Column(String)


class Contest(Base, _Exportable):
    __tablename__ = "contests"
    __updatable_keys__ = [
        "title",
        "description",
        "start_time",
        "end_time",
        "published",
        "penalty",
    ]
    __summary_keys__ = ["id", "title", "start_time", "end_time", "published"]
    id: str = Column(String, primary_key=True)
    title: str = Column(String, nullable=False)
    description: str = Column(String, nullable=False)
    start_time: datetime.datetime = Column(DateTime(timezone=True), nullable=False)
    end_time: datetime.datetime = Column(DateTime(timezone=True), nullable=False)
    published: bool = Column(Boolean, nullable=False)
    penalty: datetime.timedelta = Column(Interval, nullable=False)

    def is_begun(self) -> bool:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        return self.start_time <= now

    def is_finished(self) -> bool:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        return self.end_time <= now

    def is_accessible(self, user_info: Optional["Claims"]) -> bool:
        return self.published or (user_info is not None and user_info.admin)


class Problem(Base, _Exportable):
    __tablename__ = "problems"
    __updatable_keys__ = ["title", "description", "time_limit", "memory_limit", "score"]
    contest_id: str = Column(String, primary_key=True)
    id: str = Column(String, primary_key=True)
    title: str = Column(String, nullable=False)
    time_limit: int = Column(Integer, nullable=False)
    memory_limit: int = Column(Integer, nullable=False)  # MiB
    description: str = Column(String, nullable=False)
    score: int = Column(Integer, nullable=False)
    __table_args__ = (ForeignKeyConstraint([contest_id], [Contest.id]),)


class TestCase(Base, _Exportable):
    __tablename__ = "tests"
    contest_id: str = Column(String, primary_key=True)
    problem_id: str = Column(String, primary_key=True)
    id: str = Column(String, primary_key=True)
    input: bytes = Column(LargeBinary, nullable=False)
    output: bytes = Column(LargeBinary, nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            [contest_id, problem_id], [Problem.contest_id, Problem.id]  # type: ignore
        ),
    )


class Submission(Base, _Exportable):
    __tablename__ = "submissions"
    __summary_keys__ = [
        "contest_id",
        "problem_id",
        "id",
        "user_id",
        "code_bytes",
        "environment_id",
        "status",
        "max_time",
        "max_memory",
        "created",
    ]
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    contest_id: str = Column(String, nullable=False)
    problem_id: str = Column(String, nullable=False)
    user_id: int = Column(Integer, nullable=False)
    code: bytes = Column(LargeBinary, nullable=False)
    code_bytes: int = Column(Integer, nullable=False)
    environment_id: int = Column(Integer, nullable=False)
    status: JudgeStatus = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name, nullable=False
    )
    compile_time: datetime.timedelta | None = Column(Interval, nullable=True)
    max_time: datetime.timedelta | None = Column(Interval, nullable=True)
    max_memory: int | None = Column(Integer, nullable=True)  # KiB
    created: datetime.datetime = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    __table_args__ = (
        ForeignKeyConstraint(
            [contest_id, problem_id], [Problem.contest_id, Problem.id]  # type: ignore
        ),
        ForeignKeyConstraint([user_id], [User.id]),  # type: ignore
        ForeignKeyConstraint([environment_id], [Environment.id]),  # type: ignore
        Index("submissions_contest_problem_idx", contest_id, problem_id),
    )

    def is_accessible(self, contest: Contest, user_info: Optional["Claims"]) -> bool:
        if contest.is_finished() or (user_info and user_info.admin):
            return True
        return self.user_id == (user_info.id if user_info else None)

    @staticmethod
    def summary_fields() -> tuple[Any, ...]:
        return tuple([getattr(Submission, n) for n in Submission.__summary_keys__])


class JudgeResult(Base, _Exportable):
    __tablename__ = "judge_results"
    contest_id: str = Column(String, primary_key=True)
    problem_id: str = Column(String, primary_key=True)
    submission_id: int = Column(Integer, primary_key=True)
    test_id: str = Column(String, primary_key=True)
    status: JudgeStatus = Column(
        Enum(JudgeStatus), server_default=JudgeStatus.Waiting.name, nullable=False
    )
    time: datetime.timedelta | None = Column(Interval, nullable=True)
    memory: int | None = Column(Integer, nullable=True)  # KiB
    __table_args__ = (
        ForeignKeyConstraint([submission_id], [Submission.id]),  # type: ignore
        ForeignKeyConstraint(
            [contest_id, problem_id, test_id],  # type: ignore
            [TestCase.contest_id, TestCase.problem_id, TestCase.id],
        ),
    )


class Worker(Base, _Exportable):
    __tablename__ = "workers"
    hostname: str = Column(String, primary_key=True)
    pid: int = Column(Integer, primary_key=True)
    max_processes: int = Column(Integer, nullable=False)
    startup_time: datetime.datetime = Column(DateTime(timezone=True), nullable=False)
    last_contact: datetime.datetime = Column(DateTime(timezone=True), nullable=False)
    processed: int = Column(Integer, nullable=False)
    errors: int = Column(Integer, nullable=False)
