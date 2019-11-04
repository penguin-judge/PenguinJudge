from base64 import b64encode
from http.cookiejar import CookieJar
from datetime import datetime, timezone, timedelta
import unittest
import unittest.mock
from functools import partial
from webtest import TestApp
from zstandard import ZstdCompressor  # type: ignore
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
        def _invalid(body, setup_token=True, status=400):
            headers = self.admin_headers if setup_token else {}
            app.post_json('/users', body, headers=headers,
                          status=status if setup_token else 401)
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
        _invalid({'id': 'penguin', 'name': 'same', 'password': 'hogehoge'},
                 status=409)

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
        def _post(body, status=None):
            return app.post_json('/contests', body, headers=self.admin_headers,
                                 status=status)

        def _invalid_post(body, status=400):
            _post(body, status=status)

        def _patch(id, body, status=None):
            return app.patch_json('/contests/{}'.format(id), body,
                                  headers=self.admin_headers, status=status)

        def _invalid_patch(id, body, status=400):
            _patch(id, body, status=status)

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

        c2 = _post(c).json
        self.assertEqual(c, c2)

        _invalid_patch(c['id'], dict(end_time=start_time.isoformat()))

        patch = {
            'title': 'Hoge',
            'end_time': (end_time + timedelta(hours=1)).isoformat(),
        }
        _invalid_patch('invalid', patch, status=404)
        c3 = dict(c)
        c3.update(patch)
        c4 = _patch(c['id'], patch).json
        self.assertEqual(c3, c4)

        self.assertEqual(app.get('/contests/{}'.format(c['id'])).json, c4)
        app.get('/contests/invalid', status=404)

        c4.pop('description')
        contests = app.get('/contests').json
        self.assertEqual(len(contests), 1)
        self.assertEqual(contests[0], c4)

    def test_problem(self):
        def _post(contest_id, body, status=None):
            return app.post_json(
                '/contests/{}/problems'.format(contest_id), body,
                headers=self.admin_headers, status=status)

        def _invalid_post(contest_id, body, status=400):
            _post(contest_id, body, status=status)

        def _patch(contest_id, id, body, status=None):
            return app.patch_json(
                '/contests/{}/problems/{}'.format(contest_id, id), body,
                headers=self.admin_headers, status=status)

        def _invalid_patch(contest_id, id, body, status=400):
            _patch(contest_id, id, body, status=status)

        start_time = datetime.now(tz=timezone.utc)
        contest_id = app.post_json('/contests', {
            'id': 'abc000',
            'title': 'ABC000',
            'description': '# ABC000\n\nほげほげ\n',
            'start_time': start_time.isoformat(),
            'end_time': (start_time + timedelta(hours=1)).isoformat(),
        }, headers=self.admin_headers).json['id']

        p0 = dict(
            id='A', title='A Problem', description='# A\n', time_limit=2,
            score=100)
        _invalid_post('invalid', p0, status=404)
        _invalid_post(contest_id, {})
        _post(contest_id, p0)
        _invalid_post(contest_id, p0, status=409)

        p1 = dict(
            id='B', title='B Problem', description='# B\n', time_limit=1,
            memory_limit=1, score=200)
        _post(contest_id, p1)

        ret = app.get('/contests/{}/problems'.format(contest_id)).json
        if ret[0]['id'] != 'A':
            ret = [ret[1], ret[0]]
        p0['memory_limit'] = 256
        p0['contest_id'] = p1['contest_id'] = contest_id
        self.assertEqual([p0, p1], ret)

        _invalid_patch(contest_id, 'invalid-id', {}, status=404)
        ret = _patch(contest_id, p0['id'], {'title': 'AAAA'}).json
        p0['title'] = 'AAAA'
        self.assertEqual(ret, p0)

        app.delete('/contests/{}/problems/{}'.format(contest_id, p1['id']),
                   headers=self.admin_headers)
        self.assertEqual([p0], app.get(
            '/contests/{}/problems'.format(contest_id)).json)

        app.get('/contests/invalid/problems/invalid', status=404)
        app.get('/contests/{}/problems/invalid'.format(contest_id), status=404)
        self.assertEqual(p0, app.get(
            '/contests/{}/problems/{}'.format(contest_id, p0['id'])).json)

        ret = app.get('/contests/{}'.format(contest_id)).json
        self.assertEqual([p0], ret['problems'])

    @unittest.mock.patch('pika.BlockingConnection')
    @unittest.mock.patch('penguin_judge.api.get_mq_conn_params')
    def test_submission(self, mock_conn, mock_get_params):
        # TODO(kazuki): API経由に書き換える
        env = dict(name='Python 3.7', test_image_name='docker-image')
        with transaction() as s:
            env = Environment(**env)
            s.add(env)
            s.flush()
            env = env.to_dict()

        start_time = datetime.now(tz=timezone.utc)
        contest_id = app.post_json('/contests', {
            'id': 'abc000',
            'title': 'ABC000',
            'description': '# ABC000\n\nほげほげ\n',
            'start_time': start_time.isoformat(),
            'end_time': (start_time + timedelta(hours=1)).isoformat(),
        }, headers=self.admin_headers).json['id']
        prefix = '/contests/{}'.format(contest_id)
        app.post_json(
            '{}/problems'.format(prefix), dict(
                id='A', title='A Problem', description='# A', time_limit=2,
                score=100
            ), headers=self.admin_headers)

        # TODO(kazuki): API経由に書き換える
        ctx = ZstdCompressor()
        with transaction() as s:
            s.add(TestCase(
                contest_id=contest_id,
                problem_id='A',
                id='1',
                input=ctx.compress(b'1'),
                output=ctx.compress(b'2')))

        self.assertEqual([], app.get('{}/submissions'.format(prefix)).json)
        app.get('/contests/invalid/submissions', status=404)

        code = 'print("Hello World")'
        resp = app.post_json('{}/submissions'.format(prefix), {
            'problem_id': 'A',
            'environment_id': env['id'],
            'code': code,
        }, headers=self.admin_headers).json
        self.assertEqual([resp], app.get('{}/submissions'.format(prefix)).json)
        resp2 = app.get('{}/submissions/{}'.format(prefix, resp['id'])).json
        self.assertEqual(resp2.pop('code'), code)
        self.assertEqual(resp, resp2)

        app.post_json('{}/submissions'.format(prefix), {
            'problem_id': 'invalid',
            'environment_id': env['id'],
            'code': code,
        }, headers=self.admin_headers, status=400)
        app.post_json('{}/submissions'.format(prefix), {
            'problem_id': 'A',
            'environment_id': 99999,
            'code': code,
        }, headers=self.admin_headers, status=400)
        app.get('{}/submissions/99999'.format(prefix), status=404)

        contest_id2 = app.post_json('/contests', {
            'id': 'abc001',
            'title': 'ABC001',
            'description': '# ABC001',
            'start_time': start_time.isoformat(),
            'end_time': (start_time + timedelta(hours=1)).isoformat(),
        }, headers=self.admin_headers).json['id']
        app.get(
            '/contests/{}/submissions/{}'.format(contest_id2, resp['id']),
            status=404)
