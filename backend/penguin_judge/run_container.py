import tempfile
import os
import stat
from pathlib import Path
import requests

import docker  # type: ignore
from zstandard import ZstdDecompressor  # type: ignore

from penguin_judge.models import (
    JudgeStatus, Submission, JudgeResult, transaction)
from penguin_judge.check_result import equal_binary


def compile(task: dict, dclient: docker.DockerClient) -> dict:
    result = {'status': JudgeStatus.Running, 'exec_binary': b''}
    code = task['code']
    compile_script = task['environment']['config']['compile_script']
    srcfile_name = task['environment']['config']['srcfile_name']
    exec_binary_name = task['environment']['config']['exec_binary']

    with tempfile.TemporaryDirectory() as dname:
        with open(os.path.join(dname, srcfile_name), 'wb') as f:
            f.write(code)
        with open(os.path.join(dname, 'exec.sh'), 'w') as f:  # type: ignore
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
            result['status'] = JudgeStatus.CompilationError
        else:
            with open(os.path.join(dname, exec_binary_name), 'rb') as f:
                exec_binary = f.read()
                result['exec_binary'] = exec_binary
    return result


def check_each_test(
        task: dict, compile_result: dict,
        dclient: docker.DockerClient, test: dict) -> JudgeStatus:
    result = JudgeStatus.WrongAnswer
    env = task['environment']
    problem_info = task['problem']

    exec_script = env['config']['exec_script']
    exec_binary = compile_result['exec_binary']
    exec_binary_name = env['config']['exec_binary']

    with tempfile.TemporaryDirectory() as dname:
        exec_path = os.path.join(dname, exec_binary_name)
        with open(exec_path, 'wb') as f:
            f.write(exec_binary)
            f.close()
        mode = Path(exec_path).stat().st_mode
        Path(exec_path).chmod(mode | stat.S_IXOTH)
        with open(os.path.join(dname, 'exec.sh'), 'w') as f:  # type: ignore
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
            sock._sock.send(test['input'])
            client.wait(container['Id'], problem_info['time_limit'])
            user_output = client.logs(container, stdout=True, stderr=True)
            client.stop(container)
            client.remove_container(container)
        except requests.exceptions.ConnectionError as e:
            print(e)
            result = JudgeStatus.TimeLimitExceeded
        except Exception as e:
            print(e)
            result = JudgeStatus.RuntimeError
        else:
            if equal_binary(user_output, test['output']):
                result = JudgeStatus.Accepted

    with transaction() as s:
        s.query(JudgeResult).filter(
            JudgeResult.contest_id == task['contest_id'],
            JudgeResult.problem_id == task['problem_id'],
            JudgeResult.submission_id == task['id'],
            JudgeResult.test_id == test['id'],
        ).update({JudgeResult.status: result}, synchronize_session=False)
    return result


def check_tests(task: dict, compile_result: dict,
                dclient: docker.DockerClient) -> None:
    result = JudgeStatus.Accepted
    for test in task['tests']:
        test_result = check_each_test(task, compile_result, dclient, test)
        if test_result != JudgeStatus.Accepted:
            result = test_result
    with transaction() as s:
        s.query(Submission).filter(
            Submission.contest_id == task['contest_id'],
            Submission.problem_id == task['problem_id'],
            Submission.id == task['id']
        ).update({Submission.status: result}, synchronize_session=False)


def run(task: dict) -> None:
    print('judge start with below id')
    print('  contest_id: {}'.format(task['contest_id']))
    print('  problem_id: {}'.format(task['problem_id']))
    print('  submission_id: {}'.format(task['id']))
    print('  user_id: {}'.format(task['user_id']))

    zctx = ZstdDecompressor()
    task['code'] = zctx.decompress(task['code'])
    for test in task['tests']:
        test['input'] = zctx.decompress(test['input'])
        test['output'] = zctx.decompress(test['output'])

    docker_client = docker.from_env()
    result = compile(task, docker_client)
    if result['status'] != JudgeStatus.Running:
        with transaction() as s:
            s.query(Submission).filter(
                Submission.contest_id == task['contest_id'],
                Submission.problem_id == task['problem_id'],
                Submission.id == task['submission_id']
            ).update({
                Submission.status: result['status']
            }, synchronize_session=False)
            s.query(JudgeResult).filter(
                JudgeResult.contest_id == task['contest_id'],
                JudgeResult.problem_id == task['problem_id'],
                JudgeResult.submission_id == task['submission_id']
            ).update({
                Submission.status: result['status']
            }, synchronize_session=False)
        print('judge failed: {}'.format(result['status']))
        return

    check_tests(task, result, docker_client)
    print('judge finished')
