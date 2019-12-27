from datetime import timedelta
from logging import getLogger
from typing import Callable

from zstandard import ZstdDecompressor  # type: ignore

from penguin_judge.models import (
    JudgeStatus, Submission, JudgeResult, transaction, scoped_session)
from penguin_judge.judge import JudgeDriver, JudgeTask

LOGGER = getLogger(__name__)


def run(judge_class: Callable[[], JudgeDriver],
        task: JudgeTask) -> JudgeStatus:
    LOGGER.info('judge start (contest_id: {}, problem_id: {}, '
                'submission_id: {}, user_id: {}'.format(
                    task.contest_id, task.problem_id, task.id, task.user_id))

    def update_submission_status(
            s: scoped_session, status: JudgeStatus) -> JudgeStatus:
        s.query(Submission).filter(
            Submission.contest_id == task.contest_id,
            Submission.problem_id == task.problem_id,
            Submission.id == task.id,
        ).update({Submission.status: status}, synchronize_session=False)
        return status

    zctx = ZstdDecompressor()
    try:
        task.code = zctx.decompress(task.code)
        for test in task.tests:
            test.input = zctx.decompress(test.input)
            test.output = zctx.decompress(test.output)
    except Exception:
        LOGGER.warning('decompress failed', exc_info=True)
        with transaction() as s:
            return update_submission_status(s, JudgeStatus.InternalError)

    compile_time = None
    with judge_class() as judge:
        try:
            judge.prepare(task)
        except Exception:
            LOGGER.warning('prepare failed', exc_info=True)
            with transaction() as s:
                return update_submission_status(s, JudgeStatus.InternalError)
        if task.compile_image_name:
            ret = judge.compile(task)
            if isinstance(ret, JudgeStatus):
                with transaction() as s:
                    update_submission_status(s, ret)
                    s.query(JudgeResult).filter(
                        JudgeResult.contest_id == task.contest_id,
                        JudgeResult.problem_id == task.problem_id,
                        JudgeResult.submission_id == task.id
                    ).update({
                        JudgeResult.status: ret}, synchronize_session=False)
                LOGGER.info('judge failed (submission_id={}): {}'.format(
                    task.id, ret))
                return ret
            task.code, compile_time = ret.binary, timedelta(seconds=ret.time)
        ret, max_time, max_memory = judge.tests(task)
        with transaction() as s:
            s.query(Submission).filter(
                Submission.contest_id == task.contest_id,
                Submission.problem_id == task.problem_id,
                Submission.id == task.id
            ).update({
                Submission.status: ret,
                Submission.compile_time: compile_time,
                Submission.max_time: max_time,
                Submission.max_memory: max_memory,
            }, synchronize_session=False)
        LOGGER.info('judge finished (submission_id={}): {}'.format(
            task.id, ret))
        return ret
