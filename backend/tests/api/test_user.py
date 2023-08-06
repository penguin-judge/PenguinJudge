from base64 import b64encode
from datetime import datetime, timezone

import sqlalchemy as sa

import penguin_judge.models as m

from . import setup_db  # noqa
from . import SetupInfo, app, transaction


def test_get_current_user(setup_db: SetupInfo) -> None:
    uid, pw, name = "penguin", "password", "ABC"
    resp = app.post(
        "/users",
        json={"login_id": uid, "name": name, "password": pw},
        headers=setup_db.admin_headers,
    )
    assert resp.status_code == 201
    u = resp.json()
    token = app.post("/auth", json={"login_id": uid, "password": pw}).cookies["token"]
    assert u == app.get("/user").json()

    app.authorization = ("Bearer", token)  # type: ignore
    assert u == app.get("/user").json()
    app.authorization = None  # type: ignore
    assert u == app.get("/user", headers={"X-Auth-Token": token}).json()

    app.cookies.clear()
    resp = app.get("/user")
    assert resp.status_code == 401
    resp = app.get(
        "/user",
        headers={"X-Auth-Token": b64encode(b"invalid token").decode("ascii")},
    )
    assert resp.status_code == 401
    resp = app.get("/user", headers={"X-Auth-Token": "Z"})
    assert resp.status_code == 401

    with transaction() as s:
        s.execute(
            sa.update(m.Token)
            .where(m.Token.user_id == u["id"])
            .values(expires=datetime.now(tz=timezone.utc))
        )
    resp = app.get("/user", headers={"X-Auth-Token": token})
    assert resp.status_code == 401
