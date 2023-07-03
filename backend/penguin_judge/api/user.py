from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends

from penguin_judge.api import schemas
from penguin_judge.api.auth import Claims, require_token
from penguin_judge.db import Tx, start_transaction

router = APIRouter()


@router.get("", response_model=schemas.User, response_model_exclude_none=True)
async def get_current_user(
    claims: Claims = Depends(require_token),
    tx: Tx = Depends(start_transaction),
) -> Any:
    return asdict(claims)
