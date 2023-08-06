from typing import Any, List

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Response

from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.api.auth import Claims, require_admin_token, require_token_by_config
from penguin_judge.db import Tx, start_transaction

router = APIRouter()


@router.get(
    "", response_model=List[schemas.Environment], response_model_exclude_none=True
)
async def list_environments(
    claims: Claims = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    ret = []
    is_admin = claims and claims.admin
    q = sa.select(m.Environment)
    if not is_admin:
        q = q.where(m.Environment.published.is_(True))
    async for (row,) in await tx.session.stream(q):
        ret.append(row.to_dict() if is_admin else row.to_summary_dict())
    return ret


@router.post("", response_model=schemas.Environment, response_model_exclude_none=True)
async def register_environment(
    body: schemas.EnvironmentCreation,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    resp = await tx.session.execute(sa.insert(m.Environment).values(**body.dict()))
    (env_id,) = resp.inserted_primary_key  # type: ignore
    env = await tx.session.scalar(
        sa.select(m.Environment).where(m.Environment.id == env_id)
    )
    assert env is not None
    ret = env.to_dict()
    await tx.commit()
    return ret


@router.patch(
    "/{environment_id}",
    response_model=schemas.Environment,
    response_model_exclude_none=True,
)
async def update_environment(
    environment_id: int,
    patch: schemas.EnvironmentUpdate,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    values = {k: v for k, v in patch.dict().items() if v is not None}
    if values:
        resp = await tx.session.execute(
            sa.update(m.Environment)
            .where(m.Environment.id == environment_id)
            .values(**values)
        )
        if resp.rowcount == 0:  # type: ignore
            raise HTTPException(status_code=404)
    resp_env = await tx.session.scalar(
        sa.select(m.Environment).where(m.Environment.id == environment_id)
    )
    if not resp_env:
        raise HTTPException(status_code=404)
    env = resp_env.to_dict()
    await tx.commit()
    return env


@router.delete("/{environment_id}")
async def delete_environment(
    environment_id: int,
    claims: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Response:
    await tx.session.execute(
        sa.delete(m.Environment).where(m.Environment.id == environment_id)
    )
    await tx.commit()
    return Response(status_code=204)
