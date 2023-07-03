from typing import Any

from . import setup_db  # noqa
from . import SetupInfo, app


def test_create_user(setup_db: SetupInfo) -> None:
    def _invalid(
        body: dict[str, Any], setup_token: bool = True, status: int = 422
    ) -> None:
        headers = setup_db.admin_headers if setup_token else {}
        resp = app.post("/users", json=body, headers=headers)
        assert resp.status_code == status if setup_token else 401

    login_id, passwd = "penguin", "penguinpenguin"
    _invalid({})
    _invalid({"login_id": "abc", "name": "penguin"})
    _invalid({"login_id": "abc", "password": "penguinpenguin"})
    _invalid({"name": "abc", "password": "penguinpenguin"})
    _invalid({"login_id": "pe", "name": "ぺんぎん", "password": "penguinpenguin"})
    _invalid({"login_id": "penguin", "name": "ぺんぎん", "password": "pen"})
    _invalid({"login_id": "penguin", "name": "", "password": "penguinpenguin"})
    _invalid({"login_id": "new", "name": "new", "password": passwd}, setup_token=False)

    resp = app.post(
        "/users",
        json={"login_id": login_id, "name": "ぺんぎん", "password": passwd},
        headers=setup_db.admin_headers,
    )
    assert resp.status_code == 201
    resp_json = resp.json()
    assert len(list(resp_json.keys())) == 5
    assert isinstance(resp_json["id"], int)
    assert resp_json["login_id"] == "penguin"
    assert resp_json["name"] == "ぺんぎん"
    assert not resp_json["admin"]
    assert "created" in resp_json
    _invalid(
        {"login_id": "penguin", "name": "same", "password": "hogehoge"}, status=409
    )

    assert (
        app.post(
            "/auth",
            json={"login_id": login_id, "password": passwd},
            headers=setup_db.admin_headers,
        ).status_code
        == 200
    )
    assert (
        app.post(
            "/users", json={"login_id": "new", "name": "new", "password": passwd}
        ).status_code
        == 403
    )


def test_get_user(setup_db: SetupInfo) -> None:
    resp = app.get("/users/invalid_user")
    assert resp.status_code == 422
    resp = app.get("/users/9999999")
    assert resp.status_code == 404
    u = app.get("/users/{}".format(setup_db.admin_id)).json()
    assert u["name"] == "Administrator"
    assert u["admin"]


def test_update_user(setup_db: SetupInfo) -> None:
    login_id, passwd = "penguin", "penguinpenguin"
    resp = app.post(
        "/users",
        json={"login_id": login_id, "password": passwd, "name": "ぺんぎん"},
        headers=setup_db.admin_headers,
    )
    assert resp.status_code == 201
    u = resp.json()
    new_passwd1 = f"{passwd}1"
    new_passwd2 = f"{passwd}2"

    assert (
        app.patch(f"/users/{u['id']}", json={"new_password": new_passwd1}).status_code
        == 401
    )
    assert (
        app.patch("/users/invalid", json={"new_password": new_passwd1}).status_code
        == 401
    )
    assert (
        app.patch(
            "/users/9999999",
            json={"new_password": new_passwd1},
            headers=setup_db.admin_headers,
        ).status_code
        == 404
    )

    # force update
    assert (
        app.patch(
            f"/users/{u['id']}",
            json={"new_password": new_passwd1},
            headers=setup_db.admin_headers,
        ).status_code
        == 200
    )

    # user
    assert (
        app.post(
            "/auth", json={"login_id": login_id, "password": new_passwd1}
        ).status_code
        == 200
    )
    assert (
        app.patch(f"/users/{u['id']}", json={"new_password": new_passwd2}).status_code
        == 400
    )
    assert (
        app.patch(
            f"/users/{u['id']}",
            json={"old_password": passwd, "new_password": new_passwd2},
        ).status_code
        == 401
    )
    assert (
        app.patch(
            f"/users/{u['id']}",
            json={"old_password": new_passwd1, "new_password": new_passwd2},
        ).status_code
        == 200
    )
    assert (
        app.patch(
            f"/users/{setup_db.admin_id}",
            json={"old_password": passwd, "new_password": new_passwd1},
        ).status_code
        == 403
    )
    resp = app.patch(f"/users/{u['id']}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert app.patch(f"/users/{u['id']}", json={}).status_code == 200
