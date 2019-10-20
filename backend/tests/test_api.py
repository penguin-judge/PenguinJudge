from http.cookiejar import CookieJar
import unittest
from functools import partial
from webtest import TestApp
from penguin_judge.api import app as _app
from penguin_judge.models import (
    User, Environment, Contest, Problem, TestCase, Submission, JudgeResult,
    Token, configure, transaction)
from . import TEST_DB_URL

app = TestApp(_app, cookiejar=CookieJar())


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure(**{'sqlalchemy.url': TEST_DB_URL}, drop_all=True)

    def setUp(self):
        app.reset()
        tables = (
            JudgeResult, Submission, TestCase, Problem, Contest, Environment,
            Token, User)
        with transaction() as s:
            for t in tables:
                s.query(t).delete(synchronize_session=False)

    def test_create_user(self):
        def _invalid(body):
            app.post_json('/users', body, status=400)
        _invalid({})
        _invalid({'id': 'abc', 'name': 'penguin'})
        _invalid({'id': 'abc', 'password': 'penguinpenguin'})
        _invalid({'name': 'abc', 'password': 'penguinpenguin'})
        _invalid({'id': 'pe', 'name': 'ぺんぎん', 'password': 'penguinpenguin'})
        _invalid({'id': 'penguin', 'name': 'ぺんぎん', 'password': 'pen'})
        _invalid({'id': 'penguin', 'name': '', 'password': 'penguinpenguin'})
        resp = app.post_json('/users', {
            'id': 'penguin', 'name': 'ぺんぎん', 'password': 'penguinpenguin'
        }, status=201).json
        self.assertEqual(len(list(resp.keys())), 3)
        self.assertEqual(resp['id'], 'penguin')
        self.assertEqual(resp['name'], 'ぺんぎん')
        self.assertIn('created', resp)

    def test_auth(self):
        def _invalid(body, status=400):
            app.post_json('/auth', body, status=status)

        _notfound = partial(_invalid, status=404)
        uid, pw = 'penguin', 'password'
        app.post_json('/users', {'id': uid, 'name': '🐧', 'password': pw})
        _invalid({})
        _invalid({'id': uid})
        _invalid({'password': pw})
        _invalid({'id': 'a', 'password': pw})
        _invalid({'id': uid, 'password': 'a'})
        _notfound({'id': uid, 'password': 'wrong password'})
        _notfound({'id': 'invalid', 'password': pw})
        resp = app.post_json('/auth', {'id': uid, 'password': pw}).json
        self.assertIsInstance(resp['token'], str)
        self.assertIsInstance(resp['expires_in'], int)

    def test_get_current_user(self):
        uid, pw, name = 'penguin', 'password', '🐧'
        u = app.post_json(
            '/users', {'id': uid, 'name': name, 'password': pw}).json
        token = app.post_json(
            '/auth', {'id': uid, 'password': pw}).json['token']
        self.assertEqual(u, app.get('/user').json)
        app.reset()
        app.authorization = ('Bearer', token)
        self.assertEqual(u, app.get('/user').json)
        app.authorization = None
        self.assertEqual(u, app.get(
            '/user', headers={'X-Auth-Token': token}).json)
