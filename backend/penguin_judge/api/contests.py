from datetime import datetime, timezone
from typing import Any, List, Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query

from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.api.auth import Claims, require_admin_token, require_token_by_config
from penguin_judge.api.pagination import Pagination, PaginationResponseHeaders
from penguin_judge.db import Tx, start_transaction

router = APIRouter()


@router.get(
    "",
    responses={200: {"headers": PaginationResponseHeaders}},
    response_model=List[schemas.ContestSummary],
)
async def list_contests(
    pagination: Pagination = Depends(Pagination),
    status: Optional[schemas.ContestStatus] = Query(None),
    claims: Optional[Claims] = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    q = sa.select(m.Contest)

    # 非管理者はpublishedされているコンテスト情報のみ参照できる
    if not (claims and claims.admin):
        q = q.where(m.Contest.published.is_(True))

    if status is not None:
        now = datetime.now(tz=timezone.utc)
        if status == schemas.ContestStatus.running:
            q = q.where(sa.and_(m.Contest.start_time <= now, now < m.Contest.end_time))
        elif status == schemas.ContestStatus.scheduled:
            q = q.where(now < m.Contest.start_time)
        elif status == schemas.ContestStatus.finished:
            q = q.where(m.Contest.end_time <= now)

    q = await pagination.setup(tx, q)
    q = q.order_by(m.Contest.start_time.desc())

    ret = []
    async for c, in await tx.session.stream(q):
        ret.append(c.to_summary_dict())
    return ret


@router.post("", response_model=schemas.Contest, response_model_exclude_none=True)
async def create_contest(
    body: schemas.ContestCreation,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    if body.start_time >= body.end_time:
        raise HTTPException(400, detail="start_time must be lesser than end_time")
    try:
        await tx.session.execute(sa.insert(m.Contest).values(**body.dict()))
        contest = await tx.session.scalar(
            sa.select(m.Contest).where(m.Contest.id == body.id)
        )
        assert contest is not None
        ret = contest.to_dict()
        await tx.commit()
    except sa.exc.IntegrityError:
        raise HTTPException(status_code=409)
    return ret


@router.get(
    "/{contest_id}", response_model=schemas.Contest, response_model_exclude_none=True
)
async def get_contest(
    contest_id: str,
    claims: Optional[Claims] = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    contest = await tx.session.scalar(
        sa.select(m.Contest).where(m.Contest.id == contest_id)
    )
    if not (contest and contest.is_accessible(claims)):
        raise HTTPException(status_code=404)
    ret: dict[str, Any] = contest.to_dict()
    if contest.is_begun() or (claims and claims.admin):
        q = (
            sa.select(m.Problem)
            .where(m.Problem.contest_id == contest_id)
            .order_by(m.Problem.id)
        )
        problems = [p.to_dict() async for p in await tx.session.stream_scalars(q)]
        if problems:
            ret["problems"] = problems
    return ret


@router.patch(
    "/{contest_id}", response_model=schemas.Contest, response_model_exclude_none=True
)
async def update_contest(
    contest_id: str,
    patch: schemas.ContestUpdate,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    values = {k: v for k, v in patch.dict().items() if v is not None}
    if values:
        resp = await tx.session.execute(
            sa.update(m.Contest).where(m.Contest.id == contest_id).values(**values)
        )
        if resp.rowcount == 0:  # type: ignore
            raise HTTPException(status_code=404)
    resp_contest = await tx.session.scalar(
        sa.select(m.Contest).where(m.Contest.id == contest_id)
    )
    if not resp_contest:
        raise HTTPException(status_code=404)
    if resp_contest.start_time >= resp_contest.end_time:
        raise HTTPException(status_code=400)
    contest = resp_contest.to_dict()
    await tx.commit()
    return contest
