from base64 import b64encode
from http.cookiejar import CookieJar
from datetime import datetime, timezone, timedelta
import unittest
import unittest.mock
from functools import partial
from webtest import TestApp
from zstandard import ZstdCompressor  # type: ignore
from penguin_judge.api import app as _app, _kdf
from penguin_judge.models import (
    User, Environment, Contest, Problem, TestCase, Submission, JudgeResult,
    Token, JudgeStatus, configure, transaction)
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
        salt = b'penguin'
        passwd = _kdf('penguinpenguin', salt)
        with transaction() as s:
            for t in tables:
                s.query(t).delete(synchronize_session=False)
            s.add(User(
                id='admin', name='Administrator', salt=salt, admin=True,
                password=passwd))
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
        c['published'] = False
        self.assertEqual(c, c2)

        _invalid_patch(c['id'], dict(end_time=start_time.isoformat()))

        patch = {
            'title': 'Hoge',
            'end_time': (end_time + timedelta(hours=1)).isoformat(),
            'published': True,
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
            'published': True
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

        with transaction() as s:
            s.query(User).update({'admin': False})
            s.query(Contest).update({'start_time': (
                datetime.now(tz=timezone.utc) + timedelta(hours=1))})
        self.assertNotIn(
            'problems', app.get('/contests/{}'.format(contest_id)).json)
        app.get('/contests/{}/problems'.format(contest_id), status=403)
        app.get('/contests/{}/problems/A'.format(contest_id), status=404)

        with transaction() as s:
            s.query(Contest).update({'published': False})
        app.get('/contests/{}'.format(contest_id), status=404)
        app.get('/contests/{}/problems'.format(contest_id), status=404)
        app.get('/contests/{}/problems/A'.format(contest_id), status=404)

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
            'published': True,
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

        app.get('{}/submissions'.format(prefix), status=403)
        self.assertEqual([], app.get(
            '{}/submissions'.format(prefix), headers=self.admin_headers).json)
        app.get('/contests/invalid/submissions', status=404)

        code = 'print("Hello World")'
        resp = app.post_json('{}/submissions'.format(prefix), {
            'problem_id': 'A',
            'environment_id': env['id'],
            'code': code,
        }, headers=self.admin_headers).json
        self.assertEqual([resp], app.get(
            '{}/submissions'.format(prefix), headers=self.admin_headers).json)
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

        with transaction() as s:
            s.query(Contest).update({'end_time': start_time})
        app.get('{}/submissions'.format(prefix))

    def test_contests_pagination(self):
        test_data = []
        base_time = datetime.now(tz=timezone.utc)
        for i in range(100):
            start_time = base_time + timedelta(minutes=i * 10)
            end_time = start_time + timedelta(hours=1)
            c = {
                'id': 'id-{}'.format(i),
                'title': 'Test Contest {}'.format(i),
                'description': '**Pagination** Test {}'.format(i),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'published': True,
            }
            test_data.append(app.post_json(
                '/contests', c, headers=self.admin_headers).json)

        test_data.reverse()

        resp = app.get('/contests')
        self.assertEqual(len(resp.json), 20)
        self.assertEqual(int(resp.headers['X-Page']), 1)
        self.assertEqual(int(resp.headers['X-Per-Page']), 20)
        self.assertEqual(int(resp.headers['X-Total']), 100)
        self.assertEqual(int(resp.headers['X-Total-Pages']), 5)

        resp = app.get('/contests?page=2&per_page=31')
        self.assertEqual(len(resp.json), 31)
        self.assertEqual(
            [x['id'] for x in resp.json],
            [x['id'] for x in test_data[31:62]])
        self.assertEqual(int(resp.headers['X-Page']), 2)
        self.assertEqual(int(resp.headers['X-Per-Page']), 31)
        self.assertEqual(int(resp.headers['X-Total']), 100)
        self.assertEqual(int(resp.headers['X-Total-Pages']), 4)

    def test_submissions_pagination(self):
        test_data = []
        start_time = datetime.now(tz=timezone.utc)
        end_time = start_time + timedelta(hours=1)
        app.post_json('/contests', {
            'id': 'id0',
            'title': 'Test Contest',
            'description': '**Pagination** Test',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'published': True,
        }, headers=self.admin_headers)
        app.post_json('/contests/id0/problems', {
            'id': 'A', 'title': 'Problem', 'description': '# A',
            'time_limit': 2, 'score': 100
        }, headers=self.admin_headers)

        test_data = []
        with transaction() as s:
            env = Environment(name='Python 3.7', test_image_name='image')
            s.add(env)
            s.flush()
            for i in range(100):
                submission = Submission(
                    contest_id='id0', problem_id='A', user_id='admin',
                    code=b'dummy', environment_id=env.id)
                s.add(submission)
                s.flush()
                test_data.append(submission.to_dict())

        resp = app.get('/contests/id0/submissions', headers=self.admin_headers)
        self.assertEqual(len(resp.json), 20)
        self.assertEqual(int(resp.headers['X-Page']), 1)
        self.assertEqual(int(resp.headers['X-Per-Page']), 20)
        self.assertEqual(int(resp.headers['X-Total']), 100)
        self.assertEqual(int(resp.headers['X-Total-Pages']), 5)

        resp = app.get(
            '/contests/id0/submissions?page=2&per_page=31',
            headers=self.admin_headers)
        self.assertEqual(len(resp.json), 31)
        self.assertEqual(
            [x['id'] for x in resp.json],
            [x['id'] for x in test_data[31:62]])
        self.assertEqual(int(resp.headers['X-Page']), 2)
        self.assertEqual(int(resp.headers['X-Per-Page']), 31)
        self.assertEqual(int(resp.headers['X-Total']), 100)
        self.assertEqual(int(resp.headers['X-Total-Pages']), 4)

    def test_ranking(self):
        salt = b'penguin'
        passwd = _kdf('penguinpenguin', salt)

        app.get('/contests/abc000/rankings', status=404)

        with transaction() as s:
            env = Environment(
                name='Python3 (3.8.0)',
                test_image_name='penguin_judge_python:3.8')
            s.add(env)
            s.add(Contest(
                id='abc000',
                title='ABC000',
                description='# Title\nMarkdown Test\n\n* Item0\n* Item1\n',
                published=True,
                start_time=datetime.now(tz=timezone.utc),
                end_time=datetime.now(
                    tz=timezone.utc) + timedelta(days=365)))
            s.flush()
            env_id = env.id
            problem_ids = ['A', 'B', 'C', 'D', 'E']
            for i, id in enumerate(problem_ids):
                s.add(Problem(
                    contest_id='abc000', id=id, title='Problem {}'.format(id),
                    description='', time_limit=1, memory_limit=1024,
                    score=(i + 1) * 100))
            for i in range(10):
                s.add(User(
                    id='user{}'.format(i), name='User{}'.format(i), salt=salt,
                    password=passwd))

        self.assertEquals([], app.get('/contests/abc000/rankings').json)

        with transaction() as s:
            problem_kwargs = [dict(
                contest_id='abc000', problem_id=id, code=b'',
                environment_id=env_id) for id in problem_ids]
            start = datetime.now(tz=timezone.utc)
            d = timedelta(seconds=1)
            users = {
                'user0': [
                    (1, 0, 1), (1, 0, 2), (1, 0, 4), (1, 0, 8), (1, 0, 16)],
                'user1': [
                    (1, 1, 4), (1, 2, 8), (1, 1, 16), (1, 2, 32), (1, 1, 64)],
                'user2': [
                    (1, 1, 2), (0, 2, 0), (0, 1, 0), (0, 0, 0), (0, 0, 0)],
                'user3': [
                    (0, 1, 0), (0, 2, 0), (0, 1, 0), (0, 1, 0), (0, 1, 0)],
            }
            for u, v in users.items():
                for i, (n_ac, n_wa, t) in enumerate(v):
                    for j in range(n_wa):
                        if t > 0:
                            tmp = t - 1
                        else:
                            tmp = i + j + 1
                        s.add(Submission(
                            user_id=u, status=JudgeStatus.WrongAnswer,
                            created=start + d * tmp, **problem_kwargs[i]))
                    if n_ac > 0:
                        s.add(Submission(
                            user_id=u, status=JudgeStatus.Accepted,
                            created=start + d * t, **problem_kwargs[i]))

        ret = app.get('/contests/abc000/rankings').json
        self.assertEquals(4, len(ret))
        self.assertEquals(ret[0]['user_id'], 'user0')
        self.assertEquals(ret[1]['user_id'], 'user1')
        self.assertEquals(ret[2]['user_id'], 'user2')
        self.assertEquals(ret[3]['user_id'], 'user3')
        self.assertEquals(ret[0]['ranking'], 1)
        self.assertEquals(ret[0]['score'], 1500)
        self.assertEquals(ret[0]['penalties'], 0)
        self.assertEquals(ret[0]['time'], ret[0]['adjusted_time'])
        self.assertEquals(ret[1]['ranking'], 2)
        self.assertEquals(ret[1]['score'], 1500)
        self.assertEquals(ret[1]['penalties'], 7)
        self.assertEquals(ret[1]['time'] + 7 * 300, ret[1]['adjusted_time'])
        self.assertEquals(ret[2]['ranking'], 3)
        self.assertEquals(ret[2]['score'], 100)
        self.assertEquals(ret[2]['penalties'], 1)
        self.assertEquals(ret[2]['time'] + 300, ret[2]['adjusted_time'])
        self.assertEquals(ret[3]['ranking'], 4)
        self.assertEquals(ret[3]['score'], 0)
        self.assertEquals(ret[3]['penalties'], 0)
        self.assertEquals(ret[3]['time'], 0)
        self.assertEquals(ret[3]['problems'], {
            'A': {'penalties': 1},
            'B': {'penalties': 2},
            'C': {'penalties': 1},
            'D': {'penalties': 1},
            'E': {'penalties': 1},
        })
