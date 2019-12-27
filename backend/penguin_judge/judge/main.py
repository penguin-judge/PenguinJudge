from datetime import timedelta
from logging import getLogger
from typing import Callable, Union, List, Tuple, Optional

from zstandard import ZstdDecompressor  # type: ignore

from penguin_judge.check_result import equal_binary
from penguin_judge.models import (
    JudgeStatus, Submission, JudgeResult, transaction, scoped_session)
from penguin_judge.judge import (
    T, JudgeDriver, JudgeTask, JudgeTestInfo, AgentTestResult, AgentError)

LOGGER = getLogger(__name__)


def run(judge_class: Callable[[], JudgeDriver],
        task: JudgeTask) -> JudgeStatus:
    LOGGER.info('judge start (contest_id: {}, problem_id: {}, '
                'submission_id: {}, user_id: {}'.format(
                    task.contest_id, task.problem_id, task.id, task.user_id))
    zctx = ZstdDecompressor()
    try:
        task.code = zctx.decompress(task.code)
        for test in task.tests:
            test.input = zctx.decompress(test.input)
            test.output = zctx.decompress(test.output)
    except Exception:
        LOGGER.warning('decompress failed', exc_info=True)
        with transaction() as s:
            return _update_submission_status(s, task,
                                             JudgeStatus.InternalError)
    with judge_class() as judge:
        ret = _prepare(judge, task)
        if ret:
            return ret
        if task.compile_image_name:
            ret = _compile(judge, task)
            if ret:
                return ret
        ret = _tests(judge, task)
    LOGGER.info('judge finished (submission_id={}): {}'.format(task.id, ret))
    return ret


def _prepare(judge: JudgeDriver, task: JudgeTask) -> Union[JudgeStatus, None]:
    try:
        judge.prepare(task)
        return None
    except Exception:
        LOGGER.warning('prepare failed', exc_info=True)
        with transaction() as s:
            return _update_submission_status(
                s, task, JudgeStatus.InternalError)


def _compile(judge: JudgeDriver, task: JudgeTask) -> Union[JudgeStatus, None]:
    ret = judge.compile(task)
    if isinstance(ret, JudgeStatus):
        with transaction() as s:
            _update_submission_status(s, task, ret)
            s.query(JudgeResult).filter(
                JudgeResult.contest_id == task.contest_id,
                JudgeResult.problem_id == task.problem_id,
                JudgeResult.submission_id == task.id
            ).update({
                JudgeResult.status: ret}, synchronize_session=False)
            LOGGER.info('judge failed (submission_id={}): {}'.format(
                task.id, ret))
        return ret
    task.code, task.compile_time = ret.binary, timedelta(seconds=ret.time)
    return None


def _tests(judge: JudgeDriver, task: JudgeTask) -> JudgeStatus:
    judge_results: List[
        Tuple[JudgeStatus, Optional[timedelta], Optional[int]]] = []

    def judge_test_cmpl(
            test: JudgeTestInfo,
            resp: Union[AgentTestResult, AgentError]
    ) -> None:
        time: Optional[timedelta] = None
        memory_kb: Optional[int] = None
        if isinstance(resp, AgentTestResult):
            if resp.time is not None:
                time = timedelta(seconds=resp.time)
            if resp.memory_bytes is not None:
                memory_kb = resp.memory_bytes // 1024
            if equal_binary(test.output, resp.output):
                status = JudgeStatus.Accepted
            else:
                status = JudgeStatus.WrongAnswer
        else:
            status = JudgeStatus.from_str(resp.kind)
        judge_results.append((status, time, memory_kb))
        with transaction() as s:
            s.query(JudgeResult).filter(
                JudgeResult.contest_id == task.contest_id,
                JudgeResult.problem_id == task.problem_id,
                JudgeResult.submission_id == task.id,
                JudgeResult.test_id == test.id,
            ).update({
                JudgeResult.status: status,
                JudgeResult.time: time,
                JudgeResult.memory: memory_kb,
            }, synchronize_session=False)

    def start_test_func(test_id: str) -> None:
        with transaction() as s:
            s.query(JudgeResult).filter(
                JudgeResult.contest_id == task.contest_id,
                JudgeResult.problem_id == task.problem_id,
                JudgeResult.submission_id == task.id,
                JudgeResult.test_id == test_id,
            ).update({
                JudgeResult.status: JudgeStatus.Running
            }, synchronize_session=False)

    try:
        judge.tests(task, start_test_func, judge_test_cmpl)
    except Exception:
        LOGGER.warning(
            'test failed (submission_id={})'.format(task.id), exc_info=True)
        judge_results.append((JudgeStatus.InternalError, None, None))

    def get_submission_status() -> JudgeStatus:
        judge_status = set([s for s, _, _ in judge_results])
        if len(judge_status) == 1:
            return list(judge_status)[0]
        for x in (JudgeStatus.InternalError, JudgeStatus.RuntimeError,
                  JudgeStatus.WrongAnswer, JudgeStatus.MemoryLimitExceeded,
                  JudgeStatus.TimeLimitExceeded,
                  JudgeStatus.OutputLimitExceeded):
            if x in judge_status:
                return x
        return JudgeStatus.InternalError  # pragma: no cover

    def max_value(lst: List[T]) -> Optional[T]:
        ret = None
        for x in lst:
            if x is None:
                continue
            if ret is None or ret < x:
                ret = x
        return ret

    submission_status = get_submission_status()
    max_time = max_value([t for _, t, _ in judge_results])
    max_memory = max_value([m for _, _, m in judge_results])

    with transaction() as s:
        s.query(Submission).filter(
            Submission.contest_id == task.contest_id,
            Submission.problem_id == task.problem_id,
            Submission.id == task.id
        ).update({
            Submission.status: submission_status,
            Submission.compile_time: task.compile_time,
            Submission.max_time: max_time,
            Submission.max_memory: max_memory,
        }, synchronize_session=False)
    return submission_status


def _update_submission_status(
        s: scoped_session, task: JudgeTask, status: JudgeStatus
) -> JudgeStatus:
    s.query(Submission).filter(
        Submission.contest_id == task.contest_id,
        Submission.problem_id == task.problem_id,
        Submission.id == task.id,
    ).update({Submission.status: status}, synchronize_session=False)
    return status
