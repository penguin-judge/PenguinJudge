from contextlib import contextmanager
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor, wait
from functools import partial
import random
import time
import statistics

import common
import requests

"""テスト調整用パラメータ
"""
# テスト用ユーザ数
n_users = 150

# HTTP要求数
n_requests = 100

# ジョブあたりの要求数
n_requests_per_job = 10

# テスト用ユーザのパスワード
test_user_password = 'testtest'

# テストに使うコンテストID
contest_id = 'test'

# 投稿するコード
problems = [
    ['test', [
        ['Python', 'print("hoge")'],  # WA
        ['Python', 'print("h'],  # RE
        ['Python', 'import sys\nprint(sum([int(x) for x in sys.stdin.readline().strip().split()]))\n'],  # AC
    ]],
    ['test2', [
        ['Python', 'print("hoge")'],  # WA
        ['Python', 'print("h'],  # RE
        ['Python', 'import sys\nA, B = [int(x) for x in sys.stdin.readline().strip().split()]\nprint(int(1 / (1 / A + 1 / B)))\n'],  # AC
    ]],
]

# テストで叩くエンドポイントや処理の要求数比率調整
_TABLE = None
def test_table():
    global _TABLE
    if _TABLE:
        return _TABLE
    table = [
        [1, common.get, ('/environments',), {}, 'GET /environments'],
        [1, common.get, ('/user',), {}, 'GET /user'],
        [1, common.get, ('/contests',), {}, 'GET /contests'],
        [1 * len(problems), get_problem_detail, (), {}, 'GET /contests/*/problems/*'],
        [100, common.get, ('/contests/{}'.format(contest_id),), {}, 'GET /contests/*'],
        [100, common.get, ('/contests/{}/rankings'.format(contest_id),), {}, 'GET /contests/*/rankings'],
        [100, post_code, (), {}, 'POST /contests/*/submissions'],
    ]
    _TABLE = []
    for t in table:
        for _ in range(t[0]):
            _TABLE.append(t[1:])
    return _TABLE


# 以下は負荷テストの実装
USERS = []
ENVIRONMENTS = []
LATENCIES = {}


@contextmanager
def stopwatch(key):
    s = time.time()
    yield
    e = time.time()
    if key not in LATENCIES:
        LATENCIES[key] = []
    LATENCIES[key].append((e - s) * 1000)


def get_problem_detail():
    p = random.choice(problems)
    return common.get('/contests/{}/problems/{}'.format(contest_id, p[0]))


def post_code():
    p = random.choice(problems)
    lang, code = random.choice(p[1])
    lang, lang_id = lang.lower(), None
    for e in ENVIRONMENTS:
        if e['name'].lower().startswith(lang):
            lang_id = e['id']
            break
    return common.post_json('/contests/{}/submissions'.format(contest_id), {
        'problem_id': p[0],
        'environment_id': lang_id,
        'code': code
    })


def execute_test():
    try:
        uid, cookie = random.choice(USERS)
        common.set_cookie(cookie)
        f, args, kwargs, key = random.choice(test_table())
        with stopwatch(key):
            r = f(*args, **kwargs)
        if isinstance(r, requests.Response):
            if r.status_code >= 300:
                print(r.status_code, f, args, kwargs)
    except Exception as e:
        print(e)
        

def prepare_users():
    print('[PREPARE] テスト用ユーザアカウント作成/トークン取得中...({} users)'.format(n_users))
    for i in range(n_users):
        uid = 'test{}'.format(i)
        r = common.post_json('/users', {
            'id': uid,
            'name': 'TestUser{}'.format(i),
            'password': test_user_password,
        })
        if r.status_code in (201, 409):
            try:
                r = common.login(uid, test_user_password)
                if r.status_code == 200:
                    USERS.append([uid, r.cookies])
            except Exception:
                pass
    print('[PREPARE] {} アカウントを試験に使います'.format(len(USERS)))


def run_tests(executor):
    fs = []
    for _ in range(n_requests // n_requests_per_job):
        fs.append(executor.submit(execute_tests))
    wait(fs)
    ret = {}
    for fut in fs:
        for k, v in fut.result().items():
            if k not in ret:
                ret[k] = []
            ret[k].extend(v)
    for k, v in ret.items():
        lat_min = min(v)
        lat_max = max(v)
        lat_sum = sum(v)
        lat_avg = lat_sum / len(v)
        lat_stdev = statistics.stdev(v) if len(v) > 1 else float('nan')
        print('{}: min={:.4f}, avg={:.4f}(stdev={:.4f}), max={:.4f} (n={})'.format(
            k, lat_min, lat_avg, lat_stdev, lat_min, len(v)))


def execute_tests():
    for _ in range(n_requests_per_job):
        execute_test()
    return LATENCIES


def main():
    ENVIRONMENTS.extend(common.get('/environments').json())
    test_table()
    prepare_users()

    with ProcessPoolExecutor(
            max_workers=os.cpu_count(),
            mp_context=mp.get_context('fork'),
    ) as executor:
        try:
            common.login()
            run_tests(executor)
            executor.shutdown(wait=True)
        finally:
            common.logout()


main()
