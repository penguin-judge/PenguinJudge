from base64 import b64encode
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

import pytest
from fastapi.testclient import TestClient

import penguin_judge.models as m
from penguin_judge.api import app as _app
from penguin_judge.api.auth import _kdf

from .. import setup_module  # noqa
from .. import transaction

app = TestClient(_app)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "penguinpenguin"


class SetupInfo(NamedTuple):
    admin_id: int
    admin_token: str
    admin_headers: dict[str, str]


@pytest.fixture()
def setup_db() -> SetupInfo:
    app.cookies.clear()
    tables = (
        m.JudgeResult,
        m.Submission,
        m.TestCase,
        m.Problem,
        m.Contest,
        m.Environment,
        m.Token,
        m.User,
    )
    admin_token_bytes = bytes([i for i in range(32)])
    salt = b"penguin"
    passwd = _kdf(ADMIN_PASSWORD, salt)
    with transaction() as s:
        for t in tables:
            s.query(t).delete(synchronize_session=False)
        admin_user = m.User(
            login_id=ADMIN_USERNAME,
            name="Administrator",
            salt=salt,
            admin=True,
            password=passwd,
        )
        s.add(admin_user)
        s.flush()
        s.add(
            m.Token(
                token=admin_token_bytes,
                user_id=admin_user.id,
                expires=datetime.now(tz=timezone.utc) + timedelta(hours=1),
            )
        )
        admin_id = admin_user.id

    admin_token = b64encode(admin_token_bytes).decode("ascii")
    return SetupInfo(
        admin_id=admin_id,
        admin_token=admin_token,
        admin_headers={"X-Auth-Token": admin_token},
    )
