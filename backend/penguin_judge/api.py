from base64 import b64encode, b64decode
import datetime
from typing import Any, Union, Tuple, Optional, Dict
import pickle
from hashlib import pbkdf2_hmac
import os

import pika  # type: ignore
from flask import Flask, abort, request, Response, make_response
from zstandard import ZstdCompressor, ZstdDecompressor  # type: ignore
from openapi_core import create_spec  # type: ignore
from openapi_core.shortcuts import RequestValidator  # type: ignore
from openapi_core.wrappers.flask import FlaskOpenAPIRequest  # type: ignore
import yaml

from penguin_judge.models import (
    transaction, scoped_session,
    User, Submission, Contest, Environment, Problem, TestCase, Token,
)
from penguin_judge.mq import get_mq_conn_params
from penguin_judge.utils import json_dumps

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


def _validate_request() -> Tuple[dict, Any]:
    ret = _request_validator.validate(FlaskOpenAPIRequest(request))
    if ret.errors:
        abort(400)
    return ret.parameters, ret.body


def _validate_token(
        s: Optional[scoped_session] = None,
        required: bool = False) -> Optional[str]:
    token = request.headers.get('X-Auth-Token')
    if not token:
        items = request.headers.get('Authorization', '').split(' ', maxsplit=1)
        if len(items) == 2 and items[0].lower() == 'bearer':
            token = items[1]
    if not token:
        token = request.cookies.get('AuthToken')
    if not token:
        if required:
            abort(401)
        return None

    try:
        token_bytes = b64decode(token)
    except Exception:
        abort(401)
    utc_now = datetime.datetime.now(tz=datetime.timezone.utc)

    def _check(s: scoped_session) -> str:
        t = s.query(Token).filter(Token.token == token_bytes).first()
        if not t or t.expires <= utc_now:
            abort(401)
        return t.user_id
    if s:
        return _check(s)
    with transaction() as s:
        return _check(s)


@app.route('/auth', methods=['POST'])
def authenticate() -> Response:
    _, body = _validate_request()
    token = os.urandom(32)
    expires_in = 365 * 24 * 60 * 60
    expires = datetime.datetime.now(
        datetime.timezone.utc) + datetime.timedelta(seconds=expires_in)
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
        uid = _validate_token(s)
        if not uid:
            abort(401)
        u = s.query(User).filter(User.id == uid).first()
        assert u  # 外部キー制約でuがNoneになることは無い
        return jsonify(u.to_summary_dict())


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
        if s.query(User).filter(User.id == body.id).first():
            abort(400)
        user = User(id=body.id, password=password, name=body.name, salt=salt)
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
    # TODO(kazuki): フィルタ＆最低限の情報に絞り込み
    ret = []
    with transaction() as s:
        for c in s.query(Contest):
            ret.append(c.to_summary_dict())
    return jsonify(ret)


@app.route('/contests/<contest_id>')
def get_contest(contest_id: str) -> Response:
    with transaction() as s:
        ret = s.query(Contest).filter(Contest.id == contest_id).first()
        if not ret:
            abort(404)
        ret = ret.to_dict()
        problems = s.query(Problem).filter(
            Problem.contest_id == contest_id).all()
        if problems:
            ret['problems'] = [p.to_dict() for p in problems]
    return jsonify(ret)


@app.route('/contests/<contest_id>/submissions')
def list_own_submissions(contest_id: str) -> Response:
    ret = []
    with transaction() as s:
        submissions = s.query(Submission).filter(
                Submission.contest_id == contest_id,
                Submission.user_id == 'kazuki').all()
        if not submissions:
            abort(404)
        for c in submissions:
            ret.append(c.to_summary_dict())
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems')
def list_problems(contest_id: str) -> Response:
    with transaction() as s:
        ret = [p.to_summary_dict() for p in s.query(Problem).filter(
            Problem.contest_id == contest_id).all()]
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems/<problem_id>')
def get_problem(contest_id: str, problem_id: str) -> Response:
    with transaction() as s:
        ret = s.query(Problem).filter(
            Problem.contest_id == contest_id,
            Problem.id == problem_id).fisrt()
        if not ret:
            abort(404)
        ret = ret.to_dict()
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems/<problem_id>/submission')
def get_own_submissions(contest_id: str, problem_id: str) -> Response:
    ret = []
    zctx = ZstdDecompressor()
    with transaction() as s:
        submissions = s.query(Submission).filter(
                Submission.contest_id == contest_id,
                Submission.problem_id == problem_id,
                Submission.user_id == 'kazuki').all()
        if not submissions:
            abort(404)
        for c in submissions:
            ret.append(c.to_summary_dict())
            ret[-1]['code'] = zctx.decompress(ret[-1]['code']).decode('utf-8')
    return jsonify(ret)


@app.route('/contests/<contest_id>/problems/<problem_id>/submission',
           methods=['POST'])
def post_submission(contest_id: str, problem_id: str) -> Response:
    body = request.json
    code = body.get('code')
    env_id = body.get('environment_id')
    if not (code and env_id):
        abort(400)

    cctx = ZstdCompressor()
    code = cctx.compress(code.encode('utf8'))

    with transaction() as s:
        if not s.query(Environment).filter(Environment.id == env_id).first():
            abort(400)
        tests = s.query(TestCase).filter(
            TestCase.contest_id == contest_id,
            TestCase.problem_id == problem_id).all()
        if not tests:
            abort(400)
        submission = Submission(
            contest_id=contest_id, problem_id=problem_id,
            user_id='kazuki', code=code, environment_id=env_id)
        s.add(submission)
        s.flush()
        submission_id = submission.id

    conn = pika.BlockingConnection(get_mq_conn_params())
    ch = conn.channel()
    ch.queue_declare(queue='judge_queue')
    ch.basic_publish(
        exchange='', routing_key='judge_queue', body=pickle.dumps(
            (contest_id, problem_id, submission_id)))
    ch.close()
    conn.close()
    return make_response((b'', 201))


@app.route('/contests/<contest_id>/problems/<problem_id>/submission/all')
def get_all_submissions(contest_id: str, problem_id: str) -> Response:
    ret = []
    zctx = ZstdDecompressor()
    # TODO(bakaming) : コンテスト時間中は自分の解答だけに絞る
    with transaction() as s:
        submissions = s.query(Submission).filter(
                Submission.contest_id == contest_id,
                Submission.problem_id == problem_id).all()
        for c in submissions:
            ret.append(c.to_summary_dict())
            ret[-1]['code'] = zctx.decompress(ret[-1]['code']).decode('utf-8')
    return jsonify(ret)
