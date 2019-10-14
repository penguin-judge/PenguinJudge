import tempfile
import os
import stat
from pathlib import Path

import docker  # type: ignore
from zstandard import ZstdDecompressor  # type: ignore

from penguin_judge.models import (
    JudgeStatus, Submission, JudgeResult, transaction)
from penguin_judge.check_result import equal_binary


def compile(task: dict, dclient: docker.DockerClient) -> dict:
    result = {'status': JudgeStatus.Running, 'exec_binary': b''}
    code = task['code']
    srcfile_name = task['environment']['config']['srcfile_name']
    exec_binary_name = task['environment']['config']['exec_binary']
    compile_image_name = task['environment']['config']['compile_image_name']

    with tempfile.TemporaryDirectory() as dname:
        with open(os.path.join(dname, srcfile_name), 'wb') as f:
            f.write(code)
        try:
            client = docker.APIClient(base_url='unix:///var/run/docker.sock')
            container = client.create_container(
                compile_image_name,
                volumes=['/judge'],
                host_config=client.create_host_config(
                    binds={dname: {'bind': '/judge',
                                   'mode': 'rw', }, }),
                stdin_open=True)
            client.start(container)
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


def check_tests(task: dict, compile_result: dict,
                dclient: docker.DockerClient) -> None:
    result = JudgeStatus.Accepted

    env = task['environment']
    problem_info = task['problem']

    exec_binary = compile_result['exec_binary']
    exec_binary_name = env['config']['exec_binary']
    judge_image_name = env['config']['judge_image_name']

    with tempfile.TemporaryDirectory() as dname:
        exec_path = os.path.join(dname, exec_binary_name)
        with open(exec_path, 'wb') as f:
            f.write(exec_binary)
            f.close()
        mode = Path(exec_path).stat().st_mode
        Path(exec_path).chmod(mode | stat.S_IXOTH)
        test_dir = os.path.join(dname, 'tests/')
        os.mkdir(test_dir)
        for test in task['tests']:
            with open(os.path.join(test_dir, test['id']+'.in'), 'wb') as f:
                f.write(test['input'])
                f.close()
        try:
            client = docker.APIClient(base_url='unix:///var/run/docker.sock')
            container = client.create_container(
                judge_image_name,
                volumes=['/judge'],
                command=["sh", "/judge_scripts/judge.sh",
                         str(problem_info['time_limit'])],
                host_config=client.create_host_config(
                    binds={dname: {'bind': '/judge',
                                   'mode': 'rw', }, }),
                stdin_open=True)
            client.start(container)
            output = client.logs(container, stdout=True, stderr=True)
            print(output)
            client.stop(container)
            client.remove_container(container)
        except Exception as e:
            print(e)
            result = JudgeStatus.RuntimeError
        else:
            for test in task['tests']:
                test_result = JudgeStatus.WrongAnswer
                if os.path.exists(os.path.join(test_dir, test['id']+'.out')):
                    with open(os.path.join(test_dir,
                                           test['id']+'.out'),
                              'rb') as f:
                        user_output = f.read()
                        if equal_binary(user_output, test['output']):
                            test_result = JudgeStatus.Accepted
                else:
                    test_result = JudgeStatus.RuntimeError
                if os.path.exists(os.path.join(test_dir,
                                               test['id']+'.result')):
                    with open(os.path.join(test_dir,
                                           test['id']+'.result'),
                              'rb') as f:
                        user_result = f.read()
                        user_result = str(user_result).split() # type: ignore
                        print(user_result)
                if test_result != JudgeStatus.Accepted:
                    result = test_result
                with transaction() as s:
                    s.query(JudgeResult).filter(
                            JudgeResult.contest_id == task['contest_id'],
                            JudgeResult.problem_id == task['problem_id'],
                            JudgeResult.submission_id == task['id'],
                            JudgeResult.test_id == test['id'],
                    ).update({JudgeResult.status: result},
                             synchronize_session=False)
                    pass

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
