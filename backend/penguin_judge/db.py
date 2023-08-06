from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable, NamedTuple

import sqlalchemy as sa
import sqlalchemy.ext.asyncio as sa_asyncio
from fastapi import HTTPException

from penguin_judge import config

engine = sa_asyncio.create_async_engine(config.db_url, future=True)


class Tx(NamedTuple):
    session: sa_asyncio.AsyncSession
    transaction: sa_asyncio.AsyncSessionTransaction
    exception_handler: Callable[[Awaitable[None]], Awaitable[None]]

    async def flush(self) -> None:
        await self.exception_handler(self.session.flush())

    async def commit(self) -> None:
        await self.exception_handler(self.transaction.commit())


async def _dummy_exception_handler(awaitable: Awaitable[None]) -> None:
    await awaitable


async def _http_exception_handler(awaitable: Awaitable[None]) -> None:
    try:
        await awaitable
    except sa.exc.IntegrityError:
        raise HTTPException(status_code=409)


@asynccontextmanager
async def transaction() -> AsyncIterator[Tx]:
    """for common use.

    This transaction don't call "commit" explicitly.
    In __aexit__ calls "commit".
    """
    async with sa_asyncio.AsyncSession(engine, future=True) as session:
        async with session.begin() as transaction:
            yield Tx(session, transaction, _dummy_exception_handler)


async def start_transaction() -> AsyncIterator[Tx]:
    """for Depends (FastAPI).

    This transaction requires "commit" explicitly.
    """
    async with sa_asyncio.AsyncSession(engine, future=True) as session:
        transaction = await session.begin()
        try:
            yield Tx(session, transaction, _http_exception_handler)
        finally:
            if transaction.is_active:
                await transaction.rollback()
