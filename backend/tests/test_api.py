from base64 import b64encode
from http.cookiejar import CookieJar
from datetime import datetime, timezone, timedelta
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
        admin_token = bytes([i for i in range(32)])
        with transaction() as s:
            for t in tables:
                s.query(t).delete(synchronize_session=False)
            s.add(User(
                id='admin', name='Administrator', salt=b'penguin', admin=True,
                password=(
                    b'W\x97\xaf\xcby\xbf\x80\x03)\x8aq1\xca\xf9C \r\x18\xbeF'
                    + b'\xe4\x97.\xac\xec}\x918\xe0\xb2\x81\xd8')))
            s.flush()
            s.add(Token(
                token=admin_token, user_id='admin',
                expires=datetime.now(tz=timezone.utc) + timedelta(hours=1)))
        self.admin_token = b64encode(admin_token).decode('ascii')
        self.admin_headers = {'X-Auth-Token': self.admin_token}

    def test_create_user(self):
        def _invalid(body, setup_token=True):
            headers = self.admin_headers if setup_token else {}
            app.post_json('/users', body, headers=headers,
                          status=400 if setup_token else 401)
        _invalid({})
        _invalid({'id': 'abc', 'name': 'penguin'})
        _invalid({'id': 'abc', 'password': 'penguinpenguin'})
        _invalid({'name': 'abc', 'password': 'penguinpenguin'})
        _invalid({'id': 'pe', 'name': 'ぺんぎん', 'password': 'penguinpenguin'})
        _invalid({'id': 'penguin', 'name': 'ぺんぎん', 'password': 'pen'})
        _invalid({'id': 'penguin', 'name': '', 'password': 'penguinpenguin'})
        resp = app.post_json('/users', {
            'id': 'penguin', 'name': 'ぺんぎん', 'password': 'penguinpenguin'
        }, status=201, headers=self.admin_headers).json
        self.assertEqual(len(list(resp.keys())), 4)
        self.assertEqual(resp['id'], 'penguin')
        self.assertEqual(resp['name'], 'ぺんぎん')
        self.assertEqual(resp['admin'], False)
        self.assertIn('created', resp)
        _invalid({'id': 'penguin', 'name': 'same', 'password': 'hogehoge'})

    def test_auth(self):
        def _invalid(body, status=400):
            app.post_json('/auth', body, status=status)

        _notfound = partial(_invalid, status=404)
        uid, pw = 'penguin', 'password'
        app.post_json('/users', {'id': uid, 'name': '🐧', 'password': pw},
                      headers=self.admin_headers)
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
            '/users', {'id': uid, 'name': name, 'password': pw},
            headers=self.admin_headers).json
        token = app.post_json(
            '/auth', {'id': uid, 'password': pw}).json['token']
        self.assertEqual(u, app.get('/user').json)
        app.reset()
        app.authorization = ('Bearer', token)
        self.assertEqual(u, app.get('/user').json)
        app.authorization = None
        self.assertEqual(u, app.get(
            '/user', headers={'X-Auth-Token': token}).json)

        app.get('/user', status=401)
        app.get('/user', headers={
            'X-Auth-Token': b64encode(b'invalid token').decode('ascii')
        }, status=401)
        app.get('/user', headers={'X-Auth-Token': b'Z'}, status=401)

        with transaction() as s:
            s.query(Token).filter(Token.user_id == uid).update({
                'expires': datetime.now(tz=timezone.utc)})
        app.get('/user', headers={'X-Auth-Token': token}, status=401)

    def test_get_user(self):
        app.get('/users/invalid_user', status=404)
        u = app.get('/users/admin').json
        self.assertEqual(u['id'], 'admin')
        self.assertTrue(u['admin'])

    def test_list_environments(self):
        envs = app.get('/environments').json
        self.assertEqual(envs, [])

        env = dict(name='Python 3.7', test_image_name='docker-image')
        with transaction() as s:
            s.add(Environment(**env))
        envs = app.get('/environments').json
        self.assertEqual(len(envs), 1)
        self.assertIsInstance(envs[0]['id'], int)
        self.assertEqual(envs[0]['name'], env['name'])

    def test_create_list_modify_contest(self):
        def _invalid_post(body, status=400):
            app.post_json('/contests', body, status=status)

        def _invalid_patch(id, body, status=400):
            app.patch_json('/contests/{}'.format(id), body, status=status)

        start_time = datetime.now(tz=timezone.utc)
        end_time = start_time + timedelta(hours=1)
        c = {
            'id': 'abc000',
            'title': 'ABC000',
            'description': '# ABC000\n\nほげほげ\n',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
        }

        _invalid_post({})
        _invalid_post(dict(id='a', title='A', description='',
                           start_time=start_time.isoformat(),
                           end_time=start_time.isoformat()))

        c2 = app.post_json('/contests', c).json
        self.assertEqual(c, c2)

        _invalid_patch(c['id'], dict(end_time=start_time.isoformat()))

        patch = {
            'title': 'Hoge',
            'end_time': (end_time + timedelta(hours=1)).isoformat(),
        }
        c3 = dict(c)
        c3.update(patch)
        c4 = app.patch_json('/contests/{}'.format(c['id']), patch).json
        self.assertEqual(c3, c4)

        c4.pop('description')
        contests = app.get('/contests').json
        self.assertEqual(len(contests), 1)
        self.assertEqual(contests[0], c4)
