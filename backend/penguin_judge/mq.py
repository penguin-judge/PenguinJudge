from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator, Tuple

if TYPE_CHECKING:
    from pika import URLParameters

import aiormq

from penguin_judge import config

JUDGE_QUEUE_NAME = "judge_queue"


@asynccontextmanager
async def connect_mq() -> AsyncIterator[
    Tuple[aiormq.abc.AbstractConnection, aiormq.abc.AbstractChannel]
]:
    async with await aiormq.connect(config.mq_url) as conn:
        ch = await conn.channel()
        yield conn, ch


def get_mq_conn_params_deprecated() -> "URLParameters":
    from pika import URLParameters

    return URLParameters(config.mq_url)
