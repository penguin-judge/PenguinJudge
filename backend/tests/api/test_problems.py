from datetime import datetime, timedelta, timezone
from typing import Any, cast

from httpx import Response

import penguin_judge.models as m

from . import setup_db  # noqa
from . import SetupInfo, app, transaction


def test_problem(setup_db: SetupInfo) -> None:
    def _post(contest_id: str, body: dict[str, Any], status: int = 201) -> Response:
        resp = app.post(
            "/contests/{}/problems".format(contest_id),
            json=body,
            headers=setup_db.admin_headers,
        )
        assert resp.status_code == status
        return resp

    def _invalid_post(contest_id: str, body: dict[str, Any], status: int = 422) -> None:
        _post(contest_id, body, status=status)

    def _patch(
        contest_id: str, id: str, body: dict[str, Any], status: int = 200
    ) -> Response:
        resp = app.patch(
            "/contests/{}/problems/{}".format(contest_id, id),
            json=body,
            headers=setup_db.admin_headers,
        )
        assert resp.status_code == status
        return resp

    def _invalid_patch(
        contest_id: str, id: str, body: dict[str, Any], status: int = 422
    ) -> None:
        _patch(contest_id, id, body, status=status)

    start_time = datetime.now(tz=timezone.utc)
    contest_id = app.post(
        "/contests",
        json={
            "id": "abc000",
            "title": "ABC000",
            "description": "# ABC000\n\nほげほげ\n",
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=1)).isoformat(),
            "published": True,
        },
        headers=setup_db.admin_headers,
    ).json()["id"]

    p0 = dict(id="A", title="A Problem", description="# A\n", time_limit=2, score=100)
    _invalid_post("invalid", p0, status=404)
    _invalid_post(contest_id, {})
    _post(contest_id, p0)
    _invalid_post(contest_id, p0, status=409)

    p1 = dict(
        id="B",
        title="B Problem",
        description="# B\n",
        time_limit=1,
        memory_limit=1,
        score=200,
    )
    _post(contest_id, p1)

    ret = app.get("/contests/{}/problems".format(contest_id)).json()
    if ret[0]["id"] != "A":
        ret = [ret[1], ret[0]]
    p0["memory_limit"] = 256
    p0["contest_id"] = p1["contest_id"] = contest_id
    assert [p0, p1] == ret

    _invalid_patch(contest_id, "invalid-id", {}, status=404)
    ret = _patch(contest_id, cast(str, p0["id"]), {"title": "AAAA"}).json()
    p0["title"] = "AAAA"
    assert ret == p0

    app.delete(
        "/contests/{}/problems/{}".format(contest_id, p1["id"]),
        headers=setup_db.admin_headers,
    )
    assert [p0] == app.get("/contests/{}/problems".format(contest_id)).json()

    resp = app.get("/contests/invalid/problems/invalid")
    assert resp.status_code == 404
    resp = app.get("/contests/{}/problems/invalid".format(contest_id))
    assert resp.status_code == 404
    assert p0 == app.get("/contests/{}/problems/{}".format(contest_id, p0["id"])).json()

    ret = app.get("/contests/{}".format(contest_id)).json()
    assert [p0] == ret["problems"]

    with transaction() as s:
        s.query(m.User).update({"admin": False})
        s.query(m.Contest).update(
            {"start_time": (datetime.now(tz=timezone.utc) + timedelta(hours=1))}
        )
    assert "problems" not in app.get("/contests/{}".format(contest_id)).json()
    resp = app.get("/contests/{}/problems".format(contest_id))
    assert resp.status_code == 403
    resp = app.get("/contests/{}/problems/A".format(contest_id))
    assert resp.status_code == 404

    with transaction() as s:
        s.query(m.Contest).update({"published": False})
    resp = app.get("/contests/{}".format(contest_id))
    assert resp.status_code == 404
    resp = app.get("/contests/{}/problems".format(contest_id))
    assert resp.status_code == 404
    resp = app.get("/contests/{}/problems/A".format(contest_id))
    assert resp.status_code == 404
