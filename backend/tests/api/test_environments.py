from . import setup_db  # noqa
from . import SetupInfo, app


def test_environments(setup_db: SetupInfo) -> None:
    envs = app.get("/environments").json()
    assert envs == []

    env0 = dict(name="Python 3.11", test_image_name="python_judge_image:3.11")
    env1 = dict(
        name="Python 3.7", test_image_name="python_judge_image:3.7", published=True
    )
    for env in (env0, env1):
        resp = app.post("/environments", json=env, headers=setup_db.admin_headers)
        assert resp.status_code == 200

    envs = app.get("/environments").json()
    assert len(envs) == 1

    envs = app.get("/environments", headers=setup_db.admin_headers).json()
    assert len(envs) == 2

    tgt_id = envs[0]["id"]
    resp = app.patch(f"/environments/{tgt_id}", json=dict(name="Hoge"))
    assert resp.status_code == 401
    resp = app.patch(
        f"/environments/{tgt_id}",
        json=dict(name="Hoge"),
        headers=setup_db.admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Hoge"
    resp = app.patch(f"/environments/{tgt_id}", json={}, headers=setup_db.admin_headers)
    assert resp.status_code == 200

    resp = app.patch("/environments/99999", json={}, headers=setup_db.admin_headers)
    assert resp.status_code == 404
    resp = app.patch(
        "/environments/99999", json=dict(name="Hoge"), headers=setup_db.admin_headers
    )
    assert resp.status_code == 404

    resp = app.delete(f"/environments/{tgt_id}")
    assert resp.status_code == 401

    resp = app.delete(f"/environments/{tgt_id}", headers=setup_db.admin_headers)
    assert resp.status_code == 204
    envs = app.get("/environments", headers=setup_db.admin_headers).json()
    assert len(envs) == 1

    resp = app.delete(f"/environments/{envs[0]['id']}", headers=setup_db.admin_headers)
    assert resp.status_code == 204
    envs = app.get("/environments", headers=setup_db.admin_headers).json()
    assert len(envs) == 0
