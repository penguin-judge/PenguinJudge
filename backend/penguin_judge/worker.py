import time
from typing import Any, NamedTuple, List, Tuple, Optional

from penguin_judge.db.models import (
    TestCase, Answer, Environment, JudgeResult, JudgeStatus,
    configure, transaction
)


class JudgeTask(NamedTuple):
    contest_id: str
    problem_id: str
    answer_id: int
    user_id: str
    code: bytes
    environment_config: Any
    tests: List[Tuple[str, bytes, bytes, JudgeStatus]]


def main() -> None:
    configure()
    while True:
        judge_task: Optional[JudgeTask] = None
        with transaction() as s:
            ans = s.query(Answer).with_for_update(skip_locked=True).filter(
                Answer.status == JudgeStatus.Waiting
            ).order_by(Answer.created).first()
            if ans is not None:
                ans.status = JudgeStatus.Running
                env = s.query(Environment).filter(
                    Environment.id == ans.environment_id).first()
                test_ret_list = s.query(TestCase, JudgeResult).filter(
                    TestCase.contest_id == ans.contest_id,
                    TestCase.problem_id == ans.problem_id,
                    JudgeResult.contest_id == TestCase.contest_id,
                    JudgeResult.problem_id == TestCase.problem_id,
                    JudgeResult.test_id == TestCase.id).all()
                judge_task = JudgeTask(
                    contest_id=ans.contest_id,
                    problem_id=ans.problem_id,
                    answer_id=ans.id,
                    user_id=ans.user_id,
                    code=ans.code,
                    environment_config=env.config,
                    tests=[(t.id, t.input, t.output, r.status)
                           for (t, r) in test_ret_list])
        if not judge_task:
            time.sleep(1)
            continue
        print(judge_task)
        break


if __name__ == '__main__':
    main()
