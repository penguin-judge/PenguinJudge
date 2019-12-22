from base64 import b64encode, b64decode
from datetime import datetime, timezone, timedelta
from typing import Any, Union, Tuple, Optional, Dict, List
import pickle
from hashlib import pbkdf2_hmac
import os
from itertools import groupby
import secrets

import pika  # type: ignore
from flask import Flask, abort, request, Response, make_response, send_file
from zstandard import ZstdCompressor, ZstdDecompressor  # type: ignore
from openapi_core import create_spec  # type: ignore
from openapi_core.shortcuts import RequestValidator  # type: ignore
from openapi_core.contrib.flask import FlaskOpenAPIRequest  # type: ignore
import yaml

from penguin_judge.models import (
    transaction, scoped_session, Contest, Environment, JudgeResult,
    JudgeStatus, Problem, Submission, TestCase, Token, User, Worker)
from penguin_judge.mq import get_mq_conn_params
from penguin_judge.utils import json_dumps, pagination_header

DEFAULT_MEMORY_LIMIT = 256  # MiB

app = Flask(__name__)
with open(os.path.join(os.path.dirname(__file__), 'schema.yaml'), 'r') as f:
    _spec = create_spec(yaml.safe_load(f))
_request_validator = RequestValidator(_spec)


def response204() -> Response:
    resp = make_response((b'', 204))
    resp.headers.pop('content-type')
    return resp


def jsonify(resp: Union[dict, list], *,
            status: Optional[int] = None,
            headers: Optional[Dict[str, str]] = None) -> Response:
    return app.response_class(
        json_dumps(resp), mimetype=app.config["JSONIFY_MIMETYPE"],
        status=status, headers=headers)


def _kdf(password: str, salt: bytes) -> bytes:
    return pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)


def _validate_request() -> Tuple[Any, Any]:
    ret = _request_validator.validate(FlaskOpenAPIRequest(request))
    if ret.errors:
        abort(400)
    return ret.parameters, ret.body


def _validate_token(
        s: Optional[scoped_session] = None, required: bool = False,
        admin_required: bool = False) -> Optional[dict]:
    token = request.headers.get('X-Auth-Token')
    if not token:
        items = request.headers.get('Authorization', '').split(' ', maxsplit=1)
        if len(items) == 2 and items[0].lower() == 'bearer':
            token = items[1]
    if not token:
        token = request.cookies.get('AuthToken')
    if not token:
        if required or admin_required:
            abort(401)
        return None

    try:
        token_bytes = b64decode(token)
    except Exception:
        abort(401)
    utc_now = datetime.now(tz=timezone.utc)

    def _check(s: scoped_session) -> Optional[dict]:
        ret = s.query(Token.expires, User).filter(
            Token.token == token_bytes, Token.user_id == User.id).first()
        if not ret or ret[0] <= utc_now:
            if required or admin_required:
                abort(401)
            else:
                return None
        if admin_required and not ret[1].admin:
            abort(401)
        tmp = ret[1].to_summary_dict()
        tmp['_token_bytes'] = token_bytes
        return tmp
    if s:
        return _check(s)
    with transaction() as s:
        return _check(s)


@app.route('/auth', methods=['POST'])
def authenticate() -> Response:
    _, body = _validate_request()
    token = secrets.token_bytes()
    expires_in = 365 * 24 * 60 * 60
    expires = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    with transaction() as s:
        u = s.query(User).filter(User.id == body.id).first()
        if not u:
            abort(404)
        if u.password != _kdf(body.password, u.salt):
            abort(404)
        s.add(Token(token=token, user_id=body.id, expires=expires))
    encoded_token = b64encode(token).decode('ascii')
    headers = {
        'Set-Cookie': 'AuthToken={}; Max-Age={}'.format(
            encoded_token, expires_in)}
    return jsonify({
        'token': encoded_token, 'expires_in': expires_in}, headers=headers)


@app.route('/auth', methods=['DELETE'])
def deleteToken() -> Response:
    with transaction() as s:
        u = _validate_token(s, required=True)
        assert(u)
        s.query(Token).filter(
            Token.token == u['_token_bytes']
        ).delete(synchronize_session=False)
    resp = make_response((b'', 204))
    resp.headers.pop('content-type')
    resp.headers.add('Set-Cookie', 'AuthToken=; Max-Age=0')
    return resp


@app.route('/user')
def get_current_user() -> Response:
    with transaction() as s:
        u = _validate_token(s, required=True)
    assert(u)
    return jsonify(u)


@app.route('/users/<user_id>')
def get_user(user_id: str) -> Response:
    with transaction() as s:
        user = s.query(User).filter(User.id == user_id).first()
        if not user:
            abort(404)
        return jsonify(user.to_summary_dict())


@app.route('/users', methods=['POST'])
def create_user() -> Response:
    _, body = _validate_request()
    salt = secrets.token_bytes()
    password = _kdf(body.password, salt)
    with transaction() as s:
        u = _validate_token(s)
        admin: bool = getattr(body, 'admin', False)
        if not u or not u['admin']:
            admin = False  # 管理者のみ管理者ユーザを作成できる
        if s.query(User).filter(User.id == body.id).first():
            abort(409)
        user = User(id=body.id, password=password, name=body.name, salt=salt,
                    admin=admin)
        s.add(user)
        s.flush()
        resp = user.to_summary_dict()
    return jsonify(resp, status=201)


@app.route('/environments')
def list_environments() -> Response:
    ret = []
    with transaction() as s:
        u = _validate_token(s)
        is_admin = u and u['admin']
        q = s.query(Environment)
        if not is_admin:
            q = q.filter(Environment.published.is_(True))
        for c in q:
            ret.append(c.to_dict() if is_admin else c.to_summary_dict())
    return jsonify(ret)


@app.route('/environments', methods=['POST'])
def register_environment() -> Response:
    _, body = _validate_request()
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        e = Environment(
            name=body.name,
            active=getattr(body, 'active', True),
            published=getattr(body, 'published', False),
            compile_image_name=getattr(body, 'compile_image_name', ''),
            test_image_name=body.test_image_name)
        s.add(e)
        s.flush()
        return jsonify(e.to_dict())


@app.route('/environments/<environment_id>', methods=['PATCH'])
def update_environment(environment_id: str) -> Response:
    _, body = _validate_request()
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        c = s.query(Environment).filter(
            Environment.id == environment_id).first()
        if not c:
            abort(404)
        for key in Environment.__updatable_keys__:
            if not hasattr(body, key):
                continue
            setattr(c, key, getattr(body, key))
        ret = c.to_dict()
    return jsonify(ret)


@app.route('/environments/<environment_id>', methods=['DELETE'])
def delete_environment(environment_id: str) -> Response:
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        deleted = s.query(Environment).filter(
            Environment.id == environment_id).delete(synchronize_session=False)
        if not deleted:
            abort(404)
    return response204()


@app.route('/contests')
def list_contests() -> Response:
    params, _ = _validate_request()
    page, per_page = params.query['page'], params.query['per_page']
    ret = []
    with transaction() as s:
        u = _validate_token(s)
        q = s.query(Contest)
        if not (u and u['admin']):
            q = q.filter(Contest.published.is_(True))

        if 'status' in params.query:
            v = params.query['status']
            now = datetime.now(tz=timezone.utc)
            if v == 'running':
                q = q.filter(
                    Contest.start_time <= now,
                    now < Contest.end_time)
            elif v == 'scheduled':
                q = q.filter(now < Contest.start_time)
            elif v == 'finished':
                q = q.filter(Contest.end_time <= now)

        count = q.count()
        q = q.order_by(Contest.start_time.desc())
        for c in q.offset((page - 1) * per_page).limit(per_page):
            ret.append(c.to_summary_dict())
    return jsonify(ret, headers=pagination_header(count, page, per_page))


@app.route('/contests', methods=['POST'])
def create_contest() -> Response:
    _, body = _validate_request()
    if body.start_time >= body.end_time:
        abort(400, {'detail': 'start_time must be lesser than end_time'})
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        contest = Contest(
            id=body.id,
            title=body.title,
            description=body.description,
            start_time=body.start_time,
            end_time=body.end_time,
            published=getattr(body, 'published', None))
        s.add(contest)
        s.flush()
        ret = contest.to_dict()
    return jsonify(ret)


@app.route('/contests/<contest_id>', methods=['PATCH'])
def update_contest(contest_id: str) -> Response:
    _, body = _validate_request()
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        c = s.query(Contest).filter(Contest.id == contest_id).first()
        if not c:
            abort(404)
        for key in Contest.__updatable_keys__:
            if not hasattr(body, key):
                continue
            setattr(c, key, getattr(body, key))
        if c.start_time >= c.end_time:
            abort(400, {'detail': 'start_time must be lesser than end_time'})
        ret = c.to_dict()
    return jsonify(ret)


@app.route('/contests/<contest_id>')
def get_contest(contest_id: str) -> Response:
    with transaction() as s:
        u = _validate_token(s)
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not (contest and contest.is_accessible(u)):
            abort(404)
        ret = contest.to_dict()
        if contest.is_begun() or (u and u['admin']):
            problems = s.query(Problem).filter(
                Problem.contest_id == contest_id).all()
            if problems:
                ret['problems'] = [p.to_dict() for p in problems]
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems')
def list_problems(contest_id: str) -> Response:
    with transaction() as s:
        u = _validate_token(s)
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not (contest and contest.is_accessible(u)):
            abort(404)
        if not (contest.is_begun() or (u and u['admin'])):
            abort(403)
        ret = [p.to_summary_dict() for p in s.query(Problem).filter(
            Problem.contest_id == contest_id).all()]
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems', methods=['POST'])
def create_problem(contest_id: str) -> Response:
    _, body = _validate_request()
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        if s.query(Contest).filter(Contest.id == contest_id).count() == 0:
            abort(404)
        if s.query(Problem).filter(
                Problem.contest_id == contest_id,
                Problem.id == body.id).count() == 1:
            abort(409)
        problem = Problem(
            contest_id=contest_id,
            id=body.id,
            title=body.title,
            time_limit=body.time_limit,
            memory_limit=getattr(body, 'memory_limit', DEFAULT_MEMORY_LIMIT),
            description=body.description,
            score=body.score)
        s.add(problem)
        s.flush()
        ret = problem.to_dict()
    return jsonify(ret, status=201)


@app.route('/contests/<contest_id>/problems/<problem_id>', methods=['PATCH'])
def update_problem(contest_id: str, problem_id: str) -> Response:
    _, body = _validate_request()
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        problem = s.query(Problem).filter(Problem.contest_id == contest_id,
                                          Problem.id == problem_id).first()
        if not problem:
            abort(404)
        for key in Problem.__updatable_keys__:
            if not hasattr(body, key):
                continue
            setattr(problem, key, getattr(body, key))
        ret = problem.to_dict()
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems/<problem_id>', methods=['DELETE'])
def delete_problem(contest_id: str, problem_id: str) -> Response:
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        s.query(Problem).filter(
            Problem.contest_id == contest_id,
            Problem.id == problem_id).delete(synchronize_session=False)
    return response204()


@app.route('/contests/<contest_id>/problems/<problem_id>')
def get_problem(contest_id: str, problem_id: str) -> Response:
    with transaction() as s:
        u = _validate_token(s)
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not (contest and contest.is_accessible(u)):
            abort(404)
        if not (contest.is_begun() or (u and u['admin'])):
            abort(404)  # ここは403ではなく404にする
        ret = s.query(Problem).filter(
            Problem.contest_id == contest_id,
            Problem.id == problem_id).first()
        if not ret:
            abort(404)
        ret = ret.to_dict()
    return jsonify(ret)


@app.route('/contests/<contest_id>/submissions')
def list_submissions(contest_id: str) -> Response:
    params, body = _validate_request()
    page, per_page = params.query['page'], params.query['per_page']
    ret = []
    with transaction() as s:
        u = _validate_token(s)
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not (contest and contest.is_accessible(u)):
            abort(404)
        is_admin = (u and u['admin'])
        if not (contest.is_begun() or is_admin):
            abort(403)

        q = s.query(Submission).filter(Submission.contest_id == contest_id)
        if not (contest.is_finished() or is_admin):
            if not u:
                # 未ログイン時は開催中コンテストの投稿一覧は見えない
                abort(403)
            q = q.filter(Submission.user_id == u['id'])

        filters = [
            ('problem_id', Submission.problem_id.__eq__),
            ('environment_id', Submission.environment_id.__eq__),
            ('status', Submission.status.__eq__),
            ('user_id', Submission.user_id.contains),
        ]
        for key, expr in filters:
            v = params.query.get(key)
            if v is None:
                continue
            q = q.filter(expr(v))  # type: ignore

        count = q.count()

        if params.query.get('sort'):
            sort_keys = []
            for key in params.query['sort']:
                f = getattr(Submission, key.lstrip('-'))
                if key[0] == '-':
                    f = f.desc()
                sort_keys.append(f)
            q = q.order_by(*sort_keys)
        else:
            q = q.order_by(Submission.created)

        for c in q.offset((page - 1) * per_page).limit(per_page):
            ret.append(c.to_summary_dict())
    return jsonify(ret, headers=pagination_header(count, page, per_page))


@app.route('/contests/<contest_id>/submissions', methods=['POST'])
def post_submission(contest_id: str) -> Response:
    _, body = _validate_request()
    problem_id, code, env_id = body.problem_id, body.code, body.environment_id

    cctx = ZstdCompressor()
    code_encoded = code.encode('utf8')
    code = cctx.compress(code_encoded)

    with transaction() as s:
        u = _validate_token(s, required=True)
        assert(u)
        if not s.query(Environment).filter(Environment.id == env_id).count():
            abort(400)  # bodyが不正なので400
        if not s.query(Contest).filter(Contest.id == contest_id).count():
            abort(404)  # contest_idはURLに含まれるため404
        if not s.query(Problem).filter(Problem.contest_id == contest_id,
                                       Problem.id == problem_id).count():
            abort(400)  # bodyが不正なので400
        queued_submission_count = s.query(Submission).filter(
            Submission.user_id == u['id'],
            Submission.status.in_([JudgeStatus.Waiting, JudgeStatus.Running])
        ).count()
        if queued_submission_count > app.config['user_judge_queue_limit']:
            abort(429)
        submission = Submission(
            contest_id=contest_id, problem_id=problem_id, user_id=u['id'],
            code=code, code_bytes=len(code_encoded), environment_id=env_id)
        s.add(submission)
        s.flush()
        ret = submission.to_summary_dict()

    conn = pika.BlockingConnection(get_mq_conn_params())
    ch = conn.channel()
    ch.queue_declare(queue='judge_queue')
    ch.basic_publish(
        exchange='', routing_key='judge_queue', body=pickle.dumps(
            (contest_id, problem_id, ret['id'])))
    ch.close()
    conn.close()
    return jsonify(ret, status=201)


@app.route('/contests/<contest_id>/submissions/<submission_id>')
def get_submission(contest_id: str, submission_id: str) -> Response:
    params, _ = _validate_request()
    zctx = ZstdDecompressor()
    with transaction() as s:
        u = _validate_token(s)
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not (contest and contest.is_accessible(u)):
            abort(404)
        submission = s.query(Submission).filter(
            Submission.contest_id == contest_id,
            Submission.id == submission_id).first()
        if not submission:
            abort(404)
        if not submission.is_accessible(contest, u):
            abort(404)
        ret = submission.to_dict()
        ret['tests'] = []
        for t_raw in s.query(JudgeResult).filter(
                JudgeResult.submission_id == submission_id).order_by(
                    JudgeResult.status, JudgeResult.test_id):
            t = t_raw.to_dict()

            # 不要な情報を削除
            t.pop('contest_id')
            t.pop('problem_id')
            t.pop('submission_id')
            t['id'] = t['test_id']
            t.pop('test_id')
            if not (contest.is_finished() or (u and u['admin'])):
                # コンテスト中＆非管理者の場合は
                # 実行時間とメモリ消費量を返却しない
                # (NULLの場合はto_dictで設定されないのでpopの引数にNoneを指定)
                t.pop('time', None)
                t.pop('memory', None)
            ret['tests'].append(t)

    ret['code'] = zctx.decompress(ret['code']).decode('utf-8')
    return jsonify(ret)


@app.route('/contests/<contest_id>/rankings')
def list_rankings(contest_id: str) -> Response:
    params, _ = _validate_request()
    with transaction() as s:
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not contest:
            abort(404)
        if not contest.is_begun():
            abort(403)
        contest_penalty = contest.penalty

        problems = {p.id: p.score for p in s.query(
            Problem.id, Problem.score).filter(Problem.contest_id == contest_id)
        }

        q = s.query(
            Submission.user_id, Submission.problem_id,
            Submission.status, Submission.created,
        ).filter(
            Submission.contest_id == contest_id,
            Submission.created >= contest.start_time,
            Submission.created < contest.end_time,
        )

        users: Dict[str, List[Tuple[str, timedelta, JudgeStatus]]] = {}
        for (uid, pid, st, t) in q:
            if uid not in users:
                users[uid] = []
            users[uid].append((pid, t - contest.start_time, st))

    results = []
    for uid, all_submission in users.items():
        all_submission.sort(key=lambda x: (x[0], x[1]))
        total_time = timedelta()
        total_score = 0
        total_penalties = 0
        ret = dict(user_id=uid, problems={})
        for problem_id, submissions in groupby(
                all_submission, key=lambda x: x[0]):
            n_penalties = 0
            tmp: Dict[str, Union[float, int, timedelta]] = {}
            for (_, submit_time, submit_status) in submissions:
                if submit_status == JudgeStatus.Accepted:
                    time = tmp['time'] = submit_time
                    score = tmp['score'] = problems[problem_id]
                    total_time += time
                    total_score += score
                    total_penalties += n_penalties
                    break
                elif submit_status not in (
                        JudgeStatus.CompilationError,
                        JudgeStatus.InternalError):
                    n_penalties += 1
            tmp['penalties'] = n_penalties
            ret['problems'][problem_id] = tmp
        ret.update(dict(
            time=total_time, score=total_score, penalties=total_penalties,
            adjusted_time=total_time + total_penalties * contest_penalty))
        results.append(ret)

    results.sort(key=lambda x: (-x['score'], x['adjusted_time']))
    for i, r in enumerate(results):
        r['ranking'] = i + 1
    return jsonify(results)


@app.route('/contests/<contest_id>/problems/<problem_id>/tests')
def list_tests(contest_id: str, problem_id: str) -> Response:
    ret = []
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        q = s.query(TestCase.id).filter(
            TestCase.contest_id == contest_id,
            TestCase.problem_id == problem_id
        )
        for (test_case_id,) in q:
            ret.append(test_case_id)
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems/<problem_id>/tests',
           methods=['PUT'])
def upload_test_dataset(contest_id: str, problem_id: str) -> Response:
    from collections import Counter
    import shutil
    from zipfile import ZipFile
    from contextlib import ExitStack
    from tempfile import TemporaryFile

    zctx = ZstdCompressor()
    test_cases = []
    ret = []
    with ExitStack() as stack:
        f = stack.enter_context(TemporaryFile())
        shutil.copyfileobj(request.stream, f)
        f.seek(0)
        z = stack.enter_context(ZipFile(f))
        counts = Counter()  # type: ignore
        path_mapping = {}
        for x in z.namelist():
            if not (x.endswith('.in') or x.endswith('.out')):
                continue
            name = os.path.basename(x)
            counts.update([os.path.splitext(name)[0]])
            path_mapping[name] = x

        for k, v in counts.items():
            if v != 2:
                continue
            try:
                with z.open(path_mapping[k + '.in']) as zi:
                    in_data = zctx.compress(zi.read())
                with z.open(path_mapping[k + '.out']) as zo:
                    out_data = zctx.compress(zo.read())
            except Exception:
                continue
            test_cases.append(dict(
                contest_id=contest_id,
                problem_id=problem_id,
                id=k,
                input=in_data,
                output=out_data))
            ret.append(k)

    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        s.query(TestCase).filter(
            TestCase.contest_id == contest_id,
            TestCase.problem_id == problem_id
        ).delete()
        for kwargs in test_cases:
            s.add(TestCase(**kwargs))

    return jsonify(ret)


def _get_test_data(contest_id: str, problem_id: str, test_id: str,
                   is_input: bool) -> Response:
    from io import BytesIO
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        tc = s.query(TestCase).filter(
            TestCase.contest_id == contest_id,
            TestCase.problem_id == problem_id,
            TestCase.id == test_id).first()
        if not tc:
            abort(404)
        f = BytesIO(tc.input if is_input else tc.output)
        return send_file(
            f, as_attachment=True, attachment_filename='{}.{}'.format(
                test_id, 'in' if is_input else 'out'))


@app.route('/contests/<contest_id>/problems/<problem_id>/tests/<test_id>/in')
def get_test_input_data(contest_id: str, problem_id: str,
                        test_id: str) -> Response:
    return _get_test_data(contest_id, problem_id, test_id, True)


@app.route('/contests/<contest_id>/problems/<problem_id>/tests/<test_id>/out')
def get_test_output_data(contest_id: str, problem_id: str,
                         test_id: str) -> Response:
    return _get_test_data(contest_id, problem_id, test_id, False)


@app.route('/status')
def get_status() -> Response:
    ret = {}
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        ret['workers'] = [w.to_dict() for w in s.query(Worker)]

    conn = pika.BlockingConnection(get_mq_conn_params())
    ch = conn.channel()
    queue = ch.queue_declare(queue='judge_queue')
    ret['queued'] = queue.method.message_count
    ch.close()
    conn.close()
    return jsonify(ret)
