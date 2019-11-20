from base64 import b64encode, b64decode
from datetime import datetime, timezone, timedelta
from typing import Any, Union, Tuple, Optional, Dict, List
import pickle
from hashlib import pbkdf2_hmac
import os
from itertools import groupby

import pika  # type: ignore
from flask import Flask, abort, request, Response, make_response
from zstandard import ZstdCompressor, ZstdDecompressor  # type: ignore
from openapi_core import create_spec  # type: ignore
from openapi_core.shortcuts import RequestValidator  # type: ignore
from openapi_core.contrib.flask import FlaskOpenAPIRequest  # type: ignore
import yaml

from penguin_judge.models import (
    transaction, scoped_session, Contest, Environment, JudgeStatus, Problem,
    Submission, TestCase, Token, User,
)
from penguin_judge.mq import get_mq_conn_params
from penguin_judge.utils import json_dumps, pagination_header

DEFAULT_MEMORY_LIMIT = 256  # MiB

app = Flask(__name__)
with open(os.path.join(os.path.dirname(__file__), 'schema.yaml'), 'r') as f:
    _spec = create_spec(yaml.safe_load(f))
_request_validator = RequestValidator(_spec)


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
        return ret[1].to_summary_dict()
    if s:
        return _check(s)
    with transaction() as s:
        return _check(s)


@app.route('/auth', methods=['POST'])
def authenticate() -> Response:
    _, body = _validate_request()
    token = os.urandom(32)
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
    salt = os.urandom(16)
    password = _kdf(body.password, salt)
    with transaction() as s:
        _ = _validate_token(s, admin_required=True)
        if s.query(User).filter(User.id == body.id).first():
            abort(409)
        user = User(id=body.id, password=password, name=body.name, salt=salt,
                    admin=getattr(body, 'admin', False))
        s.add(user)
        s.flush()
        resp = user.to_summary_dict()
    return jsonify(resp, status=201)


@app.route('/environments')
def list_environments() -> Response:
    ret = []
    with transaction() as s:
        for c in s.query(Environment):
            ret.append(c.to_summary_dict())
    return jsonify(ret)


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
        if contest.is_begun():
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
        if not (contest.is_begun() or getattr(u, 'admin', False)):
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
        for key in Contest.__updatable_keys__:
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
    resp = make_response((b'', 204))
    resp.headers.pop('content-type')
    return resp


@app.route('/contests/<contest_id>/problems/<problem_id>')
def get_problem(contest_id: str, problem_id: str) -> Response:
    with transaction() as s:
        u = _validate_token(s)
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not (contest and contest.is_accessible(u)):
            abort(404)
        if not (contest.is_begun() or getattr(u, 'admin', False)):
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
    # TODO(kazuki): フィルタ＆最低限の情報に絞り込み
    params, body = _validate_request()
    page, per_page = params.query['page'], params.query['per_page']
    ret = []
    with transaction() as s:
        u = _validate_token(s)
        contest = s.query(Contest).filter(Contest.id == contest_id).first()
        if not (contest and contest.is_accessible(u)):
            abort(404)
        is_admin = getattr(u, 'admin', False)
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
        for c in q.offset((page - 1) * per_page).limit(per_page):
            ret.append(c.to_summary_dict())
    return jsonify(ret, headers=pagination_header(count, page, per_page))


@app.route('/contests/<contest_id>/submissions', methods=['POST'])
def post_submission(contest_id: str) -> Response:
    _, body = _validate_request()
    problem_id, code, env_id = body.problem_id, body.code, body.environment_id

    cctx = ZstdCompressor()
    code = cctx.compress(code.encode('utf8'))

    with transaction() as s:
        u = _validate_token(s, required=True)
        assert(u)
        if not s.query(Environment).filter(Environment.id == env_id).first():
            abort(400)
        tests = s.query(TestCase).filter(
            TestCase.contest_id == contest_id,
            TestCase.problem_id == problem_id).all()
        if not tests:
            abort(400)
        submission = Submission(
            contest_id=contest_id, problem_id=problem_id,
            user_id=u['id'], code=code, environment_id=env_id)
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
        submission = s.query(Submission).filter(
            Submission.contest_id == contest_id,
            Submission.id == submission_id).first()
        if not submission or submission.contest_id != contest_id:
            abort(404)
        ret = submission.to_dict()
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
