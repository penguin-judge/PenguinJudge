import json
import tempfile
import os
import stat
from pathlib import Path
from typing import Dict
import requests

import docker  # type: ignore

from penguin_judge.models import (
    Environment, JudgeStatus, Submission, TestCase, JudgeResult,
    Problem, transaction, scoped_session)
from penguin_judge.check_result import equal_binary


def compile(submission: Submission, s: scoped_session,
            dclient: docker.DockerClient) -> Dict:
    env = s.query(Environment).\
        filter(Environment.id == submission.environment_id).\
        all()
    result = {'status': 'fail', 'exec_binary': b''}

    if len(env) != 1:
        return result

    env = env[0]
    code = submission.code
    compile_script = env.config['compile_script']
    srcfile_name = env.config['srcfile_name']
    exec_binary_name = env.config['exec_binary']

    with tempfile.TemporaryDirectory() as dname:
        with open(os.path.join(dname, srcfile_name), 'wb') as f:
            f.write(code)
        with open(os.path.join(dname, 'exec.sh'), 'w') as f:
            f.write(compile_script)
        try:
            client = docker.APIClient(base_url='unix:///var/run/docker.sock')
            container = client.create_container(
                'judge',
                volumes=['/judge'],
                detach=True,
                host_config=client.create_host_config(
                    binds={dname: {'bind': '/judge',
                                   'mode': 'rw', }, }),
                stdin_open=True)
            client.start(container)
            client.wait(container['Id'], 30)
            compile_output = client.logs(container, stdout=True, stderr=True)
            print(compile_output)
            client.stop(container)
            client.remove_container(container)
        except Exception:
            submission.status = JudgeStatus.CompilationError
            result['status'] = 'fail'
        else:
            result['status'] = 'success'
            with open(os.path.join(dname, exec_binary_name), 'rb') as f:
                exec_binary = f.read()
                result['exec_binary'] = exec_binary
    return result


def check_each_test(submission: Submission,
                    compile_result: Dict,
                    s: scoped_session,
                    dclient: docker.DockerClient,
                    test: TestCase) -> JudgeStatus:

    result = JudgeStatus.WrongAnswer
    env = s.query(Environment).\
        filter(Environment.id == submission.environment_id).\
        all()
    if len(env) != 1:
        return result
    env = env[0]
    judge_result = s.query(JudgeResult).\
        filter(JudgeResult.contest_id == test.contest_id).\
        filter(JudgeResult.problem_id == test.problem_id).\
        filter(JudgeResult.test_id == test.id).\
        filter(JudgeResult.submission_id == submission.id).\
        all()
    if len(judge_result) != 1:
        return result
    judge_result = judge_result[0]

    problem_info = s.query(Problem).\
        filter(Problem.contest_id == test.contest_id).\
        filter(Problem.id == test.problem_id).\
        all()
    if len(problem_info) != 1:
        return result
    problem_info = problem_info[0]

    exec_script = env.config['exec_script']
    exec_binary = compile_result['exec_binary']
    exec_binary_name = env.config['exec_binary']

    with tempfile.TemporaryDirectory() as dname:
        exec_path = os.path.join(dname, exec_binary_name)
        with open(exec_path, 'wb') as f:
            f.write(exec_binary)
            f.close()
        mode = Path(exec_path).stat().st_mode
        Path(exec_path).chmod(mode | stat.S_IXOTH)
        with open(os.path.join(dname, 'exec.sh'), 'w') as f:
            f.write(exec_script)
            f.close()
        try:
            client = docker.APIClient(base_url='unix:///var/run/docker.sock')
            container = client.create_container(
                'judge',
                volumes=['/judge'],
                detach=True,
                host_config=client.create_host_config(
                    binds={dname: {'bind': '/judge',
                                   'mode': 'rw', }, }),
                stdin_open=True)
            client.start(container)
            sock = client.attach_socket(container, params={'stdin': 1,
                                                           'stream': 1})
            sock._sock.send(test.input)
            client.wait(container['Id'], problem_info.time_limit)
            user_output = client.logs(container, stdout=True, stderr=True)
            client.stop(container)
            client.remove_container(container)
        except requests.exceptions.ConnectionError as e:
            print(type(e))
            submission.status = JudgeStatus.TimeLimitExceeded
            result = JudgeStatus.TimeLimitExceeded
        except Exception as e:
            print(type(e))
            submission.status = JudgeStatus.RuntimeError
            result = JudgeStatus.RuntimeError
        else:
            if equal_binary(user_output, test.output):
                result = JudgeStatus.Accepted
        judge_result.status = result
    return result


def check_tests(submission: Submission,
                compile_result: dict,
                s: scoped_session,
                dclient: docker.DockerClient) -> None:
    testcases = s.query(TestCase).\
        filter(TestCase.contest_id == submission.contest_id).\
        filter(TestCase.problem_id == submission.problem_id).\
        all()
    result = JudgeStatus.Accepted
    for test in testcases:
        test_result = check_each_test(submission, compile_result,
                                      s, dclient, test)
        if test_result != JudgeStatus.Accepted:
            result = test_result
    submission.status = result


def run(id_information: bytes) -> None:
    id_info_dict = json.loads(id_information)

    print('judge start with below id')
    print('contest_id : ' + id_info_dict['contest_id'])
    print('problem_id : ' + id_info_dict['problem_id'])
    print('submission_id : ' + str(id_info_dict['submission_id']))
    print('user_id : ' + id_info_dict['user_id'])

    docker_client = docker.from_env()

    with transaction() as s:
        submission = s.query(Submission).\
            filter(Submission.contest_id == id_info_dict['contest_id']).\
            filter(Submission.problem_id == id_info_dict['problem_id']).\
            filter(Submission.id == id_info_dict['submission_id']).\
            filter(Submission.user_id == id_info_dict['user_id']).\
            all()
        if len(submission) == 1:
            submission = submission[0]
            result = compile(submission, s, docker_client)
            if result['status'] != 'fail':
                check_tests(submission, result, s, docker_client)
    print('judge finished')
