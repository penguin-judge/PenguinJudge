from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import scoped_session, sessionmaker

Session = scoped_session(sessionmaker())


@contextmanager
def transaction() -> Iterator[scoped_session]:
    try:
        yield Session
        Session.commit()
    except Exception:
        Session.rollback()
        raise
    finally:
        Session.remove()


def configure(**kwargs: str) -> None:
    from sqlalchemy import engine_from_config

    from penguin_judge.models import Base

    config = {k: v for k, v in kwargs.items() if k.startswith("sqlalchemy.")}
    engine = engine_from_config(config)
    Session.configure(bind=engine)  # type: ignore

    if kwargs.pop("drop_all", None):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
