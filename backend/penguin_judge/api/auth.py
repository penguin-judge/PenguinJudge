import secrets
from base64 import b64decode, b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac
from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import APIKeyCookie

from penguin_judge import config
from penguin_judge import models as m
from penguin_judge.api import schemas
from penguin_judge.db import Tx, start_transaction

router = APIRouter()
COOKIE_TOKEN_KEY = "token"
API_KEY_TOKEN = APIKeyCookie(name=COOKIE_TOKEN_KEY, auto_error=False)
VALID_DAYS = 30


@dataclass
class Claims:
    id: int
    login_id: str
    name: str
    created: datetime
    admin: bool


def _kdf(password: str, salt: bytes) -> bytes:
    return pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)


async def _get_token(
    req: Request, token: Optional[str] = Depends(API_KEY_TOKEN)
) -> Optional[bytes]:
    if not token:
        token = req.headers.get("X-Auth-Token")  # for Testing use
    if not token:
        return None
    try:
        return b64decode(token)
    except Exception:
        raise HTTPException(status_code=401)


async def _validate_token(
    token: bytes,
    tx: Tx,
    *,
    required: bool = False,
    admin_required: bool = False,
    required_by_config: bool = False,
) -> Optional[Claims]:
    assert required or admin_required or required_by_config
    if required_by_config:
        required = config.auth_required
    utc_now = datetime.now(tz=timezone.utc)
    u: Optional[m.User] = await tx.session.scalar(
        sa.select(m.User).where(
            sa.and_(
                m.Token.token == token,
                m.Token.expires > utc_now,
                m.Token.user_id == m.User.id,
            )
        )
    )
    if not u:
        if admin_required or required:
            raise HTTPException(status_code=401)
        return None
    if admin_required and not u.admin:
        raise HTTPException(status_code=403)
    return Claims(
        id=u.id,
        login_id=u.login_id,
        name=u.name,
        created=u.created,
        admin=u.admin,
    )


async def require_token(
    token: bytes = Depends(_get_token),
    tx: Tx = Depends(start_transaction),
) -> Optional[Claims]:
    return await _validate_token(token, tx, required=True)


async def require_admin_token(
    token: bytes = Depends(_get_token),
    tx: Tx = Depends(start_transaction),
) -> Optional[Claims]:
    return await _validate_token(token, tx, admin_required=True)


async def require_token_by_config(
    token: bytes = Depends(_get_token),
    tx: Tx = Depends(start_transaction),
) -> Optional[Claims]:
    return await _validate_token(token, tx, required_by_config=True)


@router.post("")
async def authenticate(
    body: schemas.Login,
    resp: Response,
    tx: Tx = Depends(start_transaction),
) -> Response:
    token = secrets.token_bytes()
    encoded_token = b64encode(token).decode("ascii")
    expires_in = VALID_DAYS * 24 * 60 * 60
    expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    u = await tx.session.scalar(
        sa.select(m.User).where(m.User.login_id == body.login_id)
    )
    if not u or u.password != _kdf(body.password, u.salt):
        raise HTTPException(status_code=401)

    await tx.session.execute(
        sa.insert(m.Token).values(token=token, user_id=u.id, expires=expires)
    )
    await tx.commit()

    resp.status_code = 200
    resp.set_cookie(
        key=COOKIE_TOKEN_KEY,
        value=encoded_token,
        httponly=True,
        samesite="strict",
        path="/",
        expires=expires_in,
    )
    return resp


@router.delete("")
async def revoke_token(
    claims: Claims = Depends(require_token),
    token: bytes = Depends(_get_token),
    tx: Tx = Depends(start_transaction),
) -> Response:
    await tx.session.execute(
        sa.delete(m.Token).where(
            sa.and_(m.Token.token == token, m.Token.user_id == claims.id)
        )
    )
    await tx.commit()
    return Response(status_code=204)
