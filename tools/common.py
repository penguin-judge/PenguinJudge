import json
import requests

from env import ADMIN_USER, ADMIN_PASS, URL

_AUTH_COOKIE = None


def get(path):
    return requests.get(
        URL + path,
        cookies=_AUTH_COOKIE)


def post_json(path, obj):
    return requests.post(
        URL + path,
        data=json.dumps(obj),
        cookies=_AUTH_COOKIE,
        headers = {'Content-Type': 'application/json'})


def patch_json(path, obj):
    return requests.patch(
        URL + path,
        data=json.dumps(obj),
        cookies=_AUTH_COOKIE,
        headers = {'Content-Type': 'application/json'})


def upload_test_dataset(contest_id, problem_id, zip_binary):
    return requests.put(
        '{}/contests/{}/problems/{}/tests'.format(URL, contest_id, problem_id),
        cookies=_AUTH_COOKIE,
        data=zip_binary,
        headers = {'Content-Type': 'application/zip'},
    )


def login():
    r = post_json('/auth', {'id': ADMIN_USER, 'password': ADMIN_PASS})
    assert r.status_code == 200
    global _AUTH_COOKIE
    _AUTH_COOKIE = r.cookies


def logout():
    r = requests.delete(URL + '/auth', cookies=_AUTH_COOKIE)
    assert r.status_code == 204
