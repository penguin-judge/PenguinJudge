from datetime import datetime, timedelta, timezone

import penguin_judge.models as m
from penguin_judge.api.auth import _kdf

from . import setup_db  # noqa
from . import SetupInfo, app, transaction


def test_ranking(setup_db: SetupInfo) -> None:
    salt = b"penguin"
    passwd = _kdf("penguinpenguin", salt)

    assert app.get("/contests/abc000/rankings").status_code == 404

    with transaction() as s:
        env = m.Environment(
            name="Python3 (3.8.0)", test_image_name="penguin_judge_python:3.8"
        )
        s.add(env)
        s.add(
            m.Contest(
                id="abc000",
                title="ABC000",
                description="# Title\nMarkdown Test\n\n* Item0\n* Item1\n",
                published=True,
                start_time=datetime.now(tz=timezone.utc),
                end_time=datetime.now(tz=timezone.utc) + timedelta(days=365),
                penalty=timedelta(seconds=300),
            )
        )
        s.flush()
        env_id = env.id
        problem_ids = ["A", "B", "C", "D", "E"]
        for i, id in enumerate(problem_ids):
            s.add(
                m.Problem(
                    contest_id="abc000",
                    id=id,
                    title="Problem {}".format(id),
                    description="",
                    time_limit=1,
                    memory_limit=1024,
                    score=(i + 1) * 100,
                )
            )
        user_mapping = {}
        for i in range(10):
            u = m.User(
                login_id="user{}".format(i),
                name="User{}".format(i),
                salt=salt,
                password=passwd,
            )
            s.add(u)
            s.flush()
            user_mapping["user{}".format(i)] = u.id

    # 未提出者もランキングに載せるようにした
    # self.assertEqual([], app.get('/contests/abc000/rankings').json)

    with transaction() as s:
        problem_kwargs = [
            dict(
                contest_id="abc000",
                problem_id=id,
                code=b"",
                code_bytes=0,
                environment_id=env_id,
            )
            for id in problem_ids
        ]
        start = datetime.now(tz=timezone.utc)
        d = timedelta(seconds=1)
        users = {
            "user0": [(1, 0, 1), (1, 0, 2), (1, 0, 4), (1, 0, 8), (1, 0, 16)],
            "user1": [(1, 1, 4), (1, 2, 8), (1, 1, 16), (1, 2, 32), (1, 1, 64)],
            "user2": [(1, 1, 2), (0, 2, 0), (0, 1, 0), (0, 0, 0), (0, 0, 0)],
            "user3": [(0, 1, 0), (0, 2, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0)],
        }
        for un, v in users.items():
            for i, (n_ac, n_wa, t) in enumerate(v):
                for j in range(n_wa):
                    if t > 0:
                        tmp = t - 1
                    else:
                        tmp = i + j + 1
                    s.add(
                        m.Submission(
                            user_id=user_mapping[un],
                            status=m.JudgeStatus.WrongAnswer,
                            created=start + d * tmp,
                            **problem_kwargs[i],
                        )
                    )
                if n_ac > 0:
                    s.add(
                        m.Submission(
                            user_id=user_mapping[un],
                            status=m.JudgeStatus.Accepted,
                            created=start + d * t,
                            **problem_kwargs[i],
                        )
                    )

    ret = app.get("/contests/abc000/rankings").json()
    # 未提出者もランキングに載せるようにした
    # self.assertEqual(4, len(ret))
    for i in range(4):
        assert ret[i]["user_id"] == user_mapping["user{}".format(i)]
        assert ret[i]["user_name"] == "User{}".format(i)
    assert ret[0]["ranking"] == 1
    assert ret[0]["score"] == 1500
    assert ret[0]["penalties"] == 0
    assert ret[0]["time"] == ret[0]["adjusted_time"]
    assert ret[1]["ranking"] == 2
    assert ret[1]["score"] == 1500
    assert ret[1]["penalties"] == 7
    assert ret[1]["time"] + 7 * 300 == ret[1]["adjusted_time"]
    assert ret[2]["ranking"] == 3
    assert ret[2]["score"] == 100
    assert ret[2]["penalties"] == 1
    assert ret[2]["time"] + 300 == ret[2]["adjusted_time"]
    assert ret[3]["ranking"] == 4
    assert ret[3]["score"] == 0
    assert ret[3]["penalties"] == 0
    assert ret[3]["time"] == 0
    assert ret[3]["problems"] == {
        "A": {"penalties": 1, "pending": False},
        "B": {"penalties": 2, "pending": False},
        "C": {"penalties": 1, "pending": False},
        "D": {"penalties": 1, "pending": False},
        "E": {"penalties": 1, "pending": False},
    }
