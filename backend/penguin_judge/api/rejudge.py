import pickle
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends

from penguin_judge import models as m
from penguin_judge.api.auth import Claims, require_admin_token
from penguin_judge.db import Tx, start_transaction
from penguin_judge.mq import JUDGE_QUEUE_NAME, connect_mq

router = APIRouter()


@router.post("")
async def rejudge(
    contest_id: str,
    problem_id: str,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    await tx.session.execute(
        sa.delete(m.JudgeResult).where(
            sa.and_(
                m.JudgeResult.contest_id == contest_id,
                m.JudgeResult.problem_id == problem_id,
            )
        )
    )
    await tx.session.execute(
        sa.update(m.Submission)
        .where(
            sa.and_(
                m.Submission.contest_id == contest_id,
                m.Submission.problem_id == problem_id,
            )
        )
        .values(status=m.JudgeStatus.Waiting)
    )
    rejudge_list = [
        x
        async for x, in await tx.session.stream(
            sa.select(m.Submission.id).where(
                sa.and_(
                    m.Submission.contest_id == contest_id,
                    m.Submission.problem_id == problem_id,
                )
            )
        )
    ]
    await tx.transaction.commit()
    async with connect_mq() as (conn, ch):
        await ch.queue_declare(JUDGE_QUEUE_NAME)
        for submission_id in rejudge_list:
            await ch.basic_publish(
                pickle.dumps((contest_id, problem_id, submission_id)),
                exchange="",
                routing_key=JUDGE_QUEUE_NAME,
            )
    return {}
