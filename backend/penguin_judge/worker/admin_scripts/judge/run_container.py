import json
import tempfile
import os
import stat
from pathlib import Path
from typing import Dict

import docker

from penguin_judge.models import (Session, Environment,
                                  JudgeStatus, Submission,
                                  TestCase, JudgeResult,
                                  configure, transaction)


def compile(submission: Submission, s: Session,
            dclient: docker.client.DockerClient) -> Dict:
    env = s.query(Environment).\
        filter(Environment.id == submission.environment_id).\
        all()
    result = {"status": "fail", "exec_binary": b''}

    if len(env) != 1:
        return result

    env = env[0]
    code = submission.code
    compile_script = env.config['compile_script']
    srcfile_name = env.config['srcfile_name']
    exec_binary_name = env.config['exec_binary']

    with tempfile.TemporaryDirectory() as dname:
        with open(os.path.join(dname, srcfile_name), "wb") as f:
            f.write(code)
            f.close()
        with open(os.path.join(dname, 'exec.sh'), "w") as f:
            f.write(compile_script)
            f.close()
        try:
            dclient.containers.run('judge',
                                   volumes={dname: {'bind': '/judge',
                                            'mode': 'rw'}},
                                   remove=True)
        except Exception:
            submission.status = JudgeStatus.CompilationError
            result["status"] = "fail"
        else:
            result["status"] = "success"
            with open(os.path.join(dname, exec_binary_name), "rb") as f:
                exec_binary = f.read()
                result["exec_binary"] = exec_binary
    return result


def check_each_test(submission: Submission,
                    compile_result: Dict,
                    s: Session,
                    dclient: docker.client.DockerClient,
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

    exec_script = env.config["exec_script"]
    exec_binary = compile_result["exec_binary"]
    exec_binary_name = env.config["exec_binary"]

    with tempfile.TemporaryDirectory() as dname:
        exec_path = os.path.join(dname, exec_binary_name)
        with open(exec_path, "wb") as f:
            f.write(exec_binary)
            f.close()
        mode = Path(exec_path).stat().st_mode
        Path(exec_path).chmod(mode | stat.S_IXOTH)
        with open(os.path.join(dname, 'exec.sh'), "w") as f:
            f.write(exec_script)
            f.close()
        with open(os.path.join(dname, 'input.in'), "wb") as f:
            f.write(test.input)
            f.close()
        try:
            dclient.containers.run('judge',
                                   volumes={dname: {'bind': '/judge',
                                            'mode': 'rw'}},
                                   remove=True)
        except Exception:
            submission.status = JudgeStatus.RuntimeError
            result = JudgeStatus.RuntimeError
        else:
            user_output = b''
            with open(os.path.join(dname, 'user.out'), "rb") as f:
                user_output = f.read()
                if user_output == test.output:
                    result = JudgeStatus.Accepted
        judge_result.status = result
    return result


def check_tests(submission: Submission,
                compile_result: dict,
                s: Session,
                dclient: docker.client.DockerClient) -> None:
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


def Run(db_hostname: str, db_port: str,
        id_information: bytes) -> None:

    id_information = json.loads(id_information)

    print("judge start with below id")
    print("contest_id : " + id_information['contest_id'])
    print("problem_id : " + id_information['problem_id'])
    print("submission_id : " + str(id_information['submission_id']))
    print("user_id : " + id_information['user_id'])

    configure(host=db_hostname, port=db_port)
    docker_client = docker.from_env()

    with transaction() as s:
        submission = s.query(Submission).\
            filter(Submission.contest_id == id_information['contest_id']).\
            filter(Submission.problem_id == id_information['problem_id']).\
            filter(Submission.id == id_information['submission_id']).\
            filter(Submission.user_id == id_information['user_id']).\
            all()

        if len(submission) == 1:
            submission = submission[0]
            result = compile(submission, s, docker_client)
            if result["status"] != "fail":
                check_tests(submission, result, s, docker_client)
    print("judge finished")


if __name__ == "__main__":
    pass
