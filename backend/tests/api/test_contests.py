from datetime import datetime, timedelta, timezone
from typing import Any, cast

from httpx import Response

from . import setup_db  # noqa
from . import SetupInfo, app


def test_create_list_modify_contest(setup_db: SetupInfo) -> None:
    def _post(body: dict[str, Any], status: int = 200) -> Response:
        resp = app.post("/contests", json=body, headers=setup_db.admin_headers)
        assert resp.status_code == status
        return resp

    def _invalid_post(body: dict[str, Any], status: int = 422) -> None:
        _post(body, status=status)

    def _patch(id: str, body: dict[str, Any], status: int = 200) -> Response:
        resp = app.patch(
            "/contests/{}".format(id),
            json=body,
            headers=setup_db.admin_headers,
        )
        assert resp.status_code == status
        return resp

    def _invalid_patch(id: str, body: dict[str, Any], status: int = 400) -> None:
        _patch(id, body, status=status)

    start_time = datetime.now(tz=timezone.utc)
    end_time = start_time + timedelta(hours=1)
    c: dict[str, str | bool | float] = {
        "id": "abc000",
        "title": "ABC000",
        "description": "# ABC000\n\nほげほげ\n",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    _invalid_post({})
    _invalid_post(
        dict(
            id="a",
            title="A",
            description="",
            start_time=start_time.isoformat(),
            end_time=start_time.isoformat(),
        ),
        status=400,
    )

    c2 = _post(c).json()
    c["published"] = False
    c["penalty"] = 300.0
    assert c == c2

    _invalid_patch(cast(str, c["id"]), dict(end_time=start_time.isoformat()))

    patch: dict[str, str | bool] = {
        "title": "Hoge",
        "end_time": (end_time + timedelta(hours=1)).isoformat(),
        "published": True,
    }
    _invalid_patch("invalid", patch, status=404)
    c3 = dict(c)
    c3.update(patch)
    c4 = _patch(cast(str, c["id"]), patch).json()
    assert c3 == c4

    assert app.get("/contests/{}".format(c["id"])).json() == c4
    resp = app.get("/contests/invalid")
    assert resp.status_code == 404

    c4.pop("description")
    c4.pop("penalty")
    contests = app.get("/contests").json()
    assert len(contests) == 1
    assert contests[0] == c4


def test_contests_pagination(setup_db: SetupInfo) -> None:
    test_data: list[dict[str, Any]] = []
    base_time = datetime.now(tz=timezone.utc)
    for i in range(100):
        start_time = base_time + timedelta(minutes=i * 10)
        end_time = start_time + timedelta(hours=1)
        c = {
            "id": "id-{}".format(i),
            "title": "Test Contest {}".format(i),
            "description": "**Pagination** Test {}".format(i),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "published": True,
        }
        test_data.append(
            app.post("/contests", json=c, headers=setup_db.admin_headers).json()
        )

    test_data.reverse()

    resp = app.get("/contests")
    assert len(resp.json()) == 20
    assert int(resp.headers["X-Page"]) == 1
    assert int(resp.headers["X-Per-Page"]) == 20
    assert int(resp.headers["X-Total"]) == 100
    assert int(resp.headers["X-Total-Pages"]) == 5

    resp = app.get("/contests?page=2&per_page=31")
    assert len(resp.json()) == 31
    assert [x["id"] for x in resp.json()] == [x["id"] for x in test_data[31:62]]
    assert int(resp.headers["X-Page"]) == 2
    assert int(resp.headers["X-Per-Page"]) == 31
    assert int(resp.headers["X-Total"]) == 100
    assert int(resp.headers["X-Total-Pages"]) == 4
