import os
from contextlib import contextmanager
from typing import Iterator

import sqlalchemy as sa
from sqlalchemy import engine_from_config
from sqlalchemy.orm import scoped_session, sessionmaker

from penguin_judge import config


def _db_url() -> str:
    if "PENGUIN_JUDGE_TEST_DB_URL" in os.environ:
        return os.environ["PENGUIN_JUDGE_TEST_DB_URL"]
    return "postgresql+psycopg://penguin:penguin@localhost:5432/penguin_judge_test"


TEST_DB_URL = _db_url()
config.db_url = TEST_DB_URL
Session = scoped_session(sessionmaker())


def setup_module() -> None:
    engine = engine_from_config(
        {
            "sqlalchemy.url": config.db_url,
        }
    )
    Session.configure(bind=engine)


@contextmanager
def transaction() -> Iterator[sa.orm.Session]:
    with Session() as session:
        with session.begin():
            yield session
