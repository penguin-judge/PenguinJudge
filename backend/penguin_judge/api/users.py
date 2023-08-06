from secrets import token_bytes
from typing import Any, Dict, Union

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException

from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.api.auth import (
    Claims,
    _kdf,
    require_admin_token,
    require_token,
    require_token_by_config,
)
from penguin_judge.db import Tx, start_transaction

router = APIRouter()


@router.post(
    "", response_model=schemas.User, status_code=201, response_model_exclude_none=True
)
async def register_user(
    body: schemas.UserRegistration,
    _: Claims = Depends(require_admin_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    salt = token_bytes()
    values = body.dict()
    values["password"] = _kdf(body.password, salt)
    try:
        (user_id,) = (
            await tx.session.execute(sa.insert(m.User).values(salt=salt, **values))
        ).inserted_primary_key  # type: ignore
    except sa.exc.IntegrityError:
        raise HTTPException(status_code=409)
    user = await tx.session.scalar(sa.select(m.User).where(m.User.id == user_id))
    assert user
    resp = user.to_dict()
    await tx.commit()
    return resp


@router.get("/{user_id}", response_model=schemas.User, response_model_exclude_none=True)
async def get_user(
    user_id: int,
    _: Claims = Depends(require_token_by_config),
    tx: Tx = Depends(start_transaction),
) -> Any:
    u = await tx.session.scalar(sa.select(m.User).where(m.User.id == user_id))
    if not u:
        raise HTTPException(status_code=404)
    return u.to_summary_dict()


@router.patch(
    "/{user_id}", response_model=schemas.User, response_model_exclude_none=True
)
async def update_user(
    user_id: int,
    patch: schemas.UserUpdate,
    claims: Claims = Depends(require_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    if user_id != claims.id and not claims.admin:
        raise HTTPException(status_code=403)
    values: Dict[str, Union[str, bytes]] = {}
    if patch.new_password:
        if not claims.admin:
            if not patch.old_password:
                raise HTTPException(status_code=400)
            u = await tx.session.scalar(sa.select(m.User).where(m.User.id == user_id))
            if not u or u.password != _kdf(patch.old_password, u.salt):
                raise HTTPException(status_code=401)
        salt = token_bytes()
        values["salt"] = salt
        values["password"] = _kdf(patch.new_password, salt)
    if patch.name:
        values["name"] = patch.name
    if values:
        update_ret = await tx.session.execute(
            sa.update(m.User).where(m.User.id == user_id).values(**values)
        )
        if update_ret.rowcount == 0:  # type: ignore
            raise HTTPException(status_code=404)
    u = await tx.session.scalar(sa.select(m.User).where(m.User.id == user_id))
    if not u:
        raise HTTPException(status_code=404)
    ret = u.to_summary_dict()
    await tx.commit()
    return ret
