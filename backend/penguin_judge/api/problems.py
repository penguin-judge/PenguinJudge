from typing import Any, List, Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException

from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.api.auth import Claims, require_admin_token, require_token_by_config
from penguin_judge.db import Tx, start_transaction

DEFAULT_MEMORY_LIMIT = 256  # MiB

router = APIRouter()


@router.get("", response_model=List[schemas.Problem])
async def list_problems(
    contest_id: str,
    claims: Optional[Claims] = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    contest = await tx.session.scalar(
        sa.select(m.Contest).where(m.Contest.id == contest_id)
    )
    if not (contest and contest.is_accessible(claims)):
        raise HTTPException(status_code=404)
    if not (contest.is_begun() or (claims and claims.admin)):
        raise HTTPException(status_code=403)
    q = (
        sa.select(m.Problem)
        .where(m.Problem.contest_id == contest_id)
        .order_by(m.Problem.id)
    )
    return [p.to_summary_dict() async for p, in await tx.session.stream(q)]


@router.post("", response_model=schemas.Problem, status_code=201)
async def create_problem(
    contest_id: str,
    body: schemas.ProblemCreation,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    q = sa.select(sa.func.count(m.Contest.id)).where(m.Contest.id == contest_id)
    if await tx.session.scalar(q) == 0:
        raise HTTPException(status_code=404)

    if body.memory_limit is None:
        body.memory_limit = DEFAULT_MEMORY_LIMIT

    try:
        await tx.session.execute(
            sa.insert(m.Problem).values(contest_id=contest_id, **body.dict())
        )
        problem = await tx.session.scalar(
            sa.select(m.Problem).where(
                sa.and_(m.Problem.contest_id == contest_id, m.Problem.id == body.id)
            )
        )
        assert problem
        ret = problem.to_dict()
        await tx.commit()
        return ret
    except sa.exc.IntegrityError:
        raise HTTPException(status_code=409)


@router.get("/{problem_id}")
async def get_problem(
    contest_id: str,
    problem_id: str,
    claims: Optional[Claims] = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    contest = await tx.session.scalar(
        sa.select(m.Contest).where(m.Contest.id == contest_id)
    )
    if not (contest and contest.is_accessible(claims)):
        raise HTTPException(status_code=404)
    if not (contest.is_begun() or (claims and claims.admin)):
        raise HTTPException(status_code=404)  # ここは403ではなく404にする
    ret = await tx.session.scalar(
        sa.select(m.Problem).where(
            sa.and_(m.Problem.contest_id == contest_id, m.Problem.id == problem_id)
        )
    )
    if not ret:
        raise HTTPException(status_code=404)
    return ret.to_dict()


@router.patch("/{problem_id}", response_model=schemas.Problem)
async def update_problem(
    contest_id: str,
    problem_id: str,
    patch: schemas.ProblemUpdate,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    values = {k: v for k, v in patch.dict().items() if v is not None}
    filter_expr = sa.and_(
        m.Problem.contest_id == contest_id, m.Problem.id == problem_id
    )
    if values:
        resp = await tx.session.execute(
            sa.update(m.Problem).where(filter_expr).values(**values)
        )
        if resp.rowcount == 0:  # type: ignore
            raise HTTPException(status_code=404)
    problem = await tx.session.scalar(sa.select(m.Problem).where(filter_expr))
    if not problem:
        raise HTTPException(status_code=404)
    ret = problem.to_dict()
    await tx.commit()
    return ret


@router.delete("/{problem_id}", status_code=204)
async def delete_problem(
    contest_id: str,
    problem_id: str,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> None:
    await tx.session.execute(
        sa.delete(m.Problem).where(
            sa.and_(m.Problem.contest_id == contest_id, m.Problem.id == problem_id)
        )
    )
    await tx.commit()
