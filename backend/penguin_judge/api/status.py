from datetime import timedelta
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends

from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.api.auth import Claims, require_admin_token
from penguin_judge.db import Tx, start_transaction
from penguin_judge.mq import JUDGE_QUEUE_NAME, connect_mq

router = APIRouter()


@router.get("", response_model=schemas.Status, response_model_exclude_none=True)
async def get_status(
    claims: Claims = Depends(require_admin_token), tx: Tx = Depends(start_transaction)
) -> Any:
    async with connect_mq() as (conn, ch):
        queued = (await ch.queue_declare(JUDGE_QUEUE_NAME)).message_count or 0
    return dict(
        workers=[
            w.to_dict()
            async for w in await tx.session.stream_scalars(
                sa.select(m.Worker)
                .where(
                    sa.func.now() - m.Worker.last_contact < timedelta(seconds=60 * 10),
                )
                .order_by(m.Worker.startup_time)
            )
        ],
        queued=queued,
    )
