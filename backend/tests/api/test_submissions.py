import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from typing import Any

from zstandard import ZstdCompressor

import penguin_judge.models as m

from . import setup_db  # noqa
from . import SetupInfo, app, transaction


@unittest.mock.patch("penguin_judge.api.submissions.connect_mq")
def test_submission(mock_connect_mq: unittest.mock.Mock, setup_db: SetupInfo) -> None:
    mock_connect_mq.return_value.__aenter__.return_value = (
        None,
        unittest.mock.AsyncMock(),
    )

    # TODO(kazuki): API経由に書き換える
    env: dict[str, Any] = dict(name="Python 3.7", test_image_name="docker-image")
    with transaction() as s:
        env = m.Environment(**env)
        s.add(env)
        s.flush()
        env = env.to_dict()

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
    prefix = "/contests/{}".format(contest_id)
    app.post(
        "{}/problems".format(prefix),
        json=dict(
            id="A", title="A Problem", description="# A", time_limit=2, score=100
        ),
        headers=setup_db.admin_headers,
    )

    # TODO(kazuki): API経由に書き換える
    ctx = ZstdCompressor()
    with transaction() as s:
        s.add(
            m.TestCase(
                contest_id=contest_id,
                problem_id="A",
                id="1",
                input=ctx.compress(b"1"),
                output=ctx.compress(b"2"),
            )
        )

    resp = app.get("{}/submissions".format(prefix))
    assert resp.status_code == 403
    assert (
        []
        == app.get(
            "{}/submissions".format(prefix), headers=setup_db.admin_headers
        ).json()
    )
    resp = app.get("/contests/invalid/submissions")
    assert resp.status_code == 404

    code = 'print("Hello World")'
    resp = app.post(
        "{}/submissions".format(prefix),
        json={
            "problem_id": "A",
            "environment_id": env["id"],
            "code": code,
        },
        headers=setup_db.admin_headers,
    )
    resp_json = resp.json()
    assert [resp_json] == app.get(
        "{}/submissions".format(prefix), headers=setup_db.admin_headers
    ).json()
    assert (
        app.get("{}/submissions/{}".format(prefix, resp_json["id"])).status_code == 404
    )

    resp2_json = app.get(
        "{}/submissions/{}".format(prefix, resp_json["id"]),
        headers=setup_db.admin_headers,
    ).json()
    assert resp2_json.pop("code") == code
    resp_json["tests"] = []
    assert resp_json == resp2_json

    assert (
        app.post(
            "{}/submissions".format(prefix),
            json={
                "problem_id": "invalid",
                "environment_id": env["id"],
                "code": code,
            },
            headers=setup_db.admin_headers,
        ).status_code
        == 400
    )
    assert (
        app.post(
            "{}/submissions".format(prefix),
            json={
                "problem_id": "A",
                "environment_id": 99999,
                "code": code,
            },
            headers=setup_db.admin_headers,
        ).status_code
        == 400
    )
    assert app.get("{}/submissions/99999".format(prefix)).status_code == 404

    contest_id2 = app.post(
        "/contests",
        json={
            "id": "abc001",
            "title": "ABC001",
            "description": "# ABC001",
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=1)).isoformat(),
        },
        headers=setup_db.admin_headers,
    ).json()["id"]
    assert (
        app.get(
            "/contests/{}/submissions/{}".format(contest_id2, resp_json["id"])
        ).status_code
        == 404
    )

    with transaction() as s:
        s.query(m.Contest).update({"end_time": start_time})
    app.get("{}/submissions".format(prefix))


def test_submissions_pagination(setup_db: SetupInfo) -> None:
    start_time = datetime.now(tz=timezone.utc)
    end_time = start_time + timedelta(hours=1)
    app.post(
        "/contests",
        json={
            "id": "id0",
            "title": "Test Contest",
            "description": "**Pagination** Test",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "published": True,
        },
        headers=setup_db.admin_headers,
    )
    app.post(
        "/contests/id0/problems",
        json={
            "id": "A",
            "title": "Problem",
            "description": "# A",
            "time_limit": 2,
            "score": 100,
        },
        headers=setup_db.admin_headers,
    )

    test_data: list[dict[str, Any]] = []
    with transaction() as s:
        env = m.Environment(name="Python 3.7", test_image_name="image")
        s.add(env)
        s.flush()
        for i in range(100):
            submission = m.Submission(
                contest_id="id0",
                problem_id="A",
                user_id=setup_db.admin_id,
                code=b"dummy",
                code_bytes=1,
                environment_id=env.id,
            )
            s.add(submission)
            s.flush()
            test_data.append(submission.to_dict())

    resp = app.get("/contests/id0/submissions", headers=setup_db.admin_headers)
    assert len(resp.json()) == 20
    assert int(resp.headers["X-Page"]) == 1
    assert int(resp.headers["X-Per-Page"]) == 20
    assert int(resp.headers["X-Total"]) == 100
    assert int(resp.headers["X-Total-Pages"]) == 5

    resp = app.get(
        "/contests/id0/submissions?page=2&per_page=31", headers=setup_db.admin_headers
    )
    assert len(resp.json()) == 31
    assert [x["id"] for x in resp.json()] == [x["id"] for x in test_data[31:62]]
    assert int(resp.headers["X-Page"]) == 2
    assert int(resp.headers["X-Per-Page"]) == 31
    assert int(resp.headers["X-Total"]) == 100
    assert int(resp.headers["X-Total-Pages"]) == 4
