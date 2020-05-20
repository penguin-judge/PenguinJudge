import json
import requests

from env import ADMIN_USER, ADMIN_PASS, URL

_AUTH_COOKIE = None
if URL.endswith('/'):
    URL = URL[:-1]


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


def set_cookie(c):
    global _AUTH_COOKIE
    _AUTH_COOKIE = c


def login(user_id = None, password = None):
    if not user_id or not password:
        user_id = ADMIN_USER
        password = ADMIN_PASS
    r = post_json('/auth', {'login_id': user_id, 'password': password})
    assert r.status_code == 200
    global _AUTH_COOKIE
    _AUTH_COOKIE = r.cookies
    return r


def logout():
    r = requests.delete(URL + '/auth', cookies=_AUTH_COOKIE)
    assert r.status_code == 204


def register(user_id, user_name, password, *, ignore_error = False):
    r = post_json('/users', {
        'login_id': user_id,
        'name': user_name,
        'password': password
    })
    if not ignore_error:
        assert r.status_code == 201
    return r
