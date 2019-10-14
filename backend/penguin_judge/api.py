from typing import Any
import pickle
import hashlib
import random

import pika  # type: ignore
from flask import Flask, jsonify, abort, request
from zstandard import ZstdCompressor, ZstdDecompressor  # type: ignore

from penguin_judge.models import (
    transaction,
    User, Submission, Contest, Environment, Problem, TestCase,
)
from penguin_judge.mq import get_mq_conn_params

app = Flask(__name__)


@app.route('/user/<user_id>')
def get_user(user_id: str) -> Any:
    ret = []
    with transaction() as s:
        users = s.query(User).filter(User.id == user_id).all()
        if not users:
            abort(404)
        for c in users:
            ret.append(c.to_summary_dict())
    return jsonify(ret)


@app.route('/user', methods=['POST'])
def create_user() -> Any:
    body = request.json
    password = body.get('password')
    user_name = body.get('name')
    if not (password and user_name):
        abort(400)
    with transaction() as s:
        prev_check = s.query(User).filter(User.name == user_name).all()
        if prev_check:
            abort(400)
        id = hashlib.sha1(user_name.encode('utf-8')).hexdigest()[:15]
        salt = hashlib.sha1(str(random.random()).encode('utf-8')).\
            hexdigest().encode('utf-8')
        password = hashlib.sha1((password + salt.decode('utf-8')).
                                encode('utf-8')).hexdigest().encode('utf-8')
        user = User(
            id=id, password=password, name=user_name, salt=salt)
        s.add(user)
        s.flush()
    return b'', 201


@app.route('/environments')
def list_environments() -> Any:
    ret = []
    with transaction() as s:
        for c in s.query(Environment):
            ret.append(c.to_summary_dict())
    return jsonify(ret)


@app.route('/contests')
def list_contests() -> Any:
    # TODO(kazuki): フィルタ＆最低限の情報に絞り込み
    ret = []
    with transaction() as s:
        for c in s.query(Contest):
            ret.append(c.to_summary_dict())
    return jsonify(ret)


@app.route('/contests/<contest_id>')
def get_contest(contest_id: str) -> Any:
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


@app.route('/contests/<contest_id>/problems/<problem_id>/submission')
def get_own_submissions(contest_id: str, problem_id: str) -> Any:
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
def post_submission(contest_id: str, problem_id: str) -> Any:
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
    return b'', 201


@app.route('/contests/<contest_id>/problems/<problem_id>/submission/all')
def get_all_submissions(contest_id: str, problem_id: str) -> Any:
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
