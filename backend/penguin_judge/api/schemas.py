from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# TODO(*): 制約の定義を共通化する (https://github.com/samuelcolvin/pydantic/issues/2129)
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 256
NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 256
LOGIN_ID_MIN_LENGTH = NAME_MIN_LENGTH
LOGIN_ID_MAX_LENGTH = NAME_MAX_LENGTH
CONTEST_ID_RE = r"[^\~]\w*"
PROBLEM_ID_RE = CONTEST_ID_RE


class Login(BaseModel):
    login_id: str = Field(
        ..., min_length=LOGIN_ID_MIN_LENGTH, max_length=LOGIN_ID_MAX_LENGTH
    )
    password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )


class UserBase(BaseModel):
    name: str = Field(..., min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    admin: bool = Field(False)


class User(UserBase):
    id: int = Field(...)
    created: datetime = Field(...)
    login_id: Optional[str] = Field(
        None, min_length=LOGIN_ID_MIN_LENGTH, max_length=LOGIN_ID_MAX_LENGTH
    )


class UserUpdate(BaseModel):
    old_password: Optional[str] = Field(
        None, min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    new_password: Optional[str] = Field(
        None, min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    name: Optional[str] = Field(
        None, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH
    )


class UserRegistration(UserBase, Login):
    pass


class EnvironmentBase(BaseModel):
    name: str = Field(...)
    active: bool = Field(True)
    published: bool = Field(False)
    compile_image_name: Optional[str] = Field(None)


class Environment(EnvironmentBase):
    id: int = Field(...)
    test_image_name: Optional[str] = Field(None)


class EnvironmentCreation(EnvironmentBase):
    test_image_name: str = Field(...)


class EnvironmentUpdate(BaseModel):
    name: Optional[str]
    active: Optional[bool]
    published: Optional[bool]
    compile_image_name: Optional[str]
    test_image_name: Optional[str]


class ContestStatus(str, Enum):
    scheduled = "scheduled"
    running = "running"
    finished = "finished"


class ContestSummary(BaseModel):
    id: str = Field(..., regex=CONTEST_ID_RE)
    title: str = Field(...)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    published: bool = Field(False)


class Contest(ContestSummary):
    penalty: timedelta = Field(...)
    description: str = Field(...)
    problems: List["Problem"] | None = Field(None)


class ContestCreation(ContestSummary):
    penalty: timedelta = Field(timedelta(seconds=300))
    description: str = Field(...)


class ContestUpdate(BaseModel):
    title: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    start_time: Optional[datetime] = Field(None)
    end_time: Optional[datetime] = Field(None)
    published: Optional[bool] = Field(None)
    penalty: Optional[timedelta] = Field(None)


class ProblemBase(BaseModel):
    id: str = Field(..., regex=PROBLEM_ID_RE)
    title: str = Field(...)
    description: str = Field(...)
    time_limit: int = Field(..., title="[sec]")
    memory_limit: Optional[int] = Field(None, title="[MiB]")
    score: int = Field(...)


class Problem(ProblemBase):
    contest_id: str = Field(..., regex=CONTEST_ID_RE)


class ProblemCreation(ProblemBase):
    pass


class ProblemUpdate(BaseModel):
    title: str | None
    description: str | None
    time_limit: int | None = Field(title="[sec]")
    memory_limit: int | None = Field(title="[MiB]")
    score: int | None


class WorkerStatus(BaseModel):
    hostname: str = Field(...)
    pid: int = Field(...)
    startup_time: datetime = Field(...)
    last_contact: datetime = Field(...)
    processed: int = Field(...)
    errors: int = Field(...)


class Status(BaseModel):
    queued: int = Field(..., title="ジャッジキューに積まれているタスクの数")
    workers: List[WorkerStatus] = Field(...)


class RankingProblemEntry(BaseModel):
    score: Optional[int] = Field(None)
    time: Optional[float] = Field(None)
    penalties: int = Field(...)
    pending: bool = Field(..., description="ジャッジ中(Waiting/Running)の投稿がある場合はTrueとなる")


class RankingEntry(BaseModel):
    ranking: int = Field(...)
    user_id: int = Field(...)
    user_name: Optional[str] = Field(None)
    score: Optional[int] = Field(None)
    time: Optional[float] = Field(None)
    penalties: Optional[int] = Field(None)
    adjusted_time: Optional[float] = Field(None, description="ペナルティを加算後の所要時間")
    problems: Dict[str, RankingProblemEntry] = Field(..., description="keyは問題ID")


class JudgeStatus(str, Enum):
    waiting = "Waiting"
    running = "Running"
    accepted = "Accepted"
    compilation_error = "CompilationError"
    runtime_error = "RuntimeError"
    wrong_answer = "WrongAnswer"
    memory_limit_exceeded = "MemoryLimitExceeded"
    time_limit_exceeded = "TimeLimitExceeded"
    output_limit_exceeded = "OutputLimitExceeded"
    internal_error = "InternalError"


class SubmissionBase(BaseModel):
    problem_id: str
    environment_id: int


class SubmissionSummary(SubmissionBase):
    contest_id: str
    id: int
    user_id: int
    user_name: str
    status: JudgeStatus
    code_bytes: int | None
    max_time: int | None
    max_memory: int | None
    created: datetime


class TestResult(BaseModel):
    id: str
    status: JudgeStatus
    time: float | None
    memory: int | None


class SubmissionPost(SubmissionBase):
    code: str


class Submission(SubmissionSummary):
    code: str
    tests: list[TestResult]


Contest.update_forward_refs()
