import email
from datetime import datetime, timedelta
from functools import partial
from http.cookies import SimpleCookie
from typing import Any

from penguin_judge.api.auth import VALID_DAYS

from . import setup_db  # noqa
from . import SetupInfo, app


def test_auth(setup_db: SetupInfo) -> None:
    def _invalid(body: dict[str, Any], status: int = 422) -> None:
        resp = app.post("/auth", json=body)
        assert status == resp.status_code

    _auth_failed = partial(_invalid, status=401)
    uid, pw = "penguin", "password"
    resp = app.post(
        "/users",
        json={"login_id": uid, "name": "ABC", "password": pw},
        headers=setup_db.admin_headers,
    )
    _invalid({})
    _invalid({"login_id": uid})
    _invalid({"password": pw})
    _invalid({"login_id": "a", "password": pw})
    _invalid({"login_id": uid, "password": "a"})
    _auth_failed({"login_id": uid, "password": "wrong password"})
    _auth_failed({"login_id": "invalid", "password": pw})
    resp = app.post("/auth", json={"login_id": uid, "password": pw})
    cookie: SimpleCookie[str] = SimpleCookie(resp.headers["Set-Cookie"])
    assert isinstance(cookie["token"].value, str)
    assert isinstance(cookie["token"]["expires"], str)
    expires_in = datetime.utcfromtimestamp(
        email.utils.parsedate_to_datetime(cookie["token"]["expires"]).timestamp()
    )
    assert expires_in < datetime.utcnow() + timedelta(days=VALID_DAYS)
    assert expires_in > datetime.utcnow() + timedelta(days=(VALID_DAYS - 1))

    # revoke test
    assert app.get("/user").status_code == 200
    assert app.delete("/auth").status_code == 204
    assert app.get("/user").status_code == 401
