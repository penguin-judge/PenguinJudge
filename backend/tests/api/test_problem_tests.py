from datetime import datetime, timedelta, timezone
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from . import setup_db  # noqa
from . import SetupInfo, app


def test_problem_tests(setup_db: SetupInfo) -> None:
    contest_id = app.post(
        "/contests",
        json=dict(
            id="abc000",
            title="ABC000",
            description="# ABC000",
            start_time=datetime.now(tz=timezone.utc).isoformat(),
            end_time=(datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat(),
            published=True,
        ),
        headers=setup_db.admin_headers,
    ).json()["id"]
    problem_id = app.post(
        f"/contests/{contest_id}/problems",
        json=dict(
            id="A",
            title="A Problem",
            description="# A",
            time_limit=1,
            memory_limit=1,
            score=100,
        ),
        headers=setup_db.admin_headers,
    ).json()["id"]

    zip_bytes_io = BytesIO()
    with ZipFile(zip_bytes_io, mode="w", compression=ZIP_DEFLATED) as z:
        with z.open("1.in", mode="w") as f:
            f.write(b"1")
        with z.open("1.out", mode="w") as f:
            f.write(b"1111")
        with z.open("2.in", mode="w") as f:
            f.write(b"2")
        with z.open("2.out", mode="w") as f:
            f.write(b"2222")
    zip_bytes = zip_bytes_io.getvalue()

    resp = app.put(
        f"/contests/{contest_id}/problems/{problem_id}/tests",
        content=zip_bytes,
        headers=setup_db.admin_headers | {"Content-Type": "application/zip"},
    )
    assert resp.status_code == 200
    assert resp.json() == ["1", "2"]

    resp = app.get(
        f"/contests/{contest_id}/problems/{problem_id}/tests",
        headers=setup_db.admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == ["1", "2"]

    for test_id in ("1", "2"):
        for in_out, data in (("in", test_id), ("out", test_id * 4)):
            resp = app.get(
                f"/contests/{contest_id}/problems/{problem_id}/tests/{test_id}/{in_out}",
                headers=setup_db.admin_headers,
            )
            assert resp.status_code == 200
            assert resp.read() == data.encode("ascii")
    resp = app.get(
        f"/contests/{contest_id}/problems/{problem_id}/tests/9999/in",
        headers=setup_db.admin_headers,
    )
    assert resp.status_code == 404
