import time
from argparse import ArgumentParser
import pika
import json
import docker
import sys
sys.path.append('../../db')
from model.model import *
import tarfile
import tempfile
import os
import stat
from pathlib import Path

def compile(db_hostname, db_port, submit, s, dclient):
    env = s.query(Environment).\
        filter(Environment.id == submit.environment_id).\
        all()
    code = submit.code
    compile_script = env[0].config['compile']
    result = {"status" : "fail", "exec_binary" : b''}
    with tempfile.TemporaryDirectory() as dname:
        with open(os.path.join(dname, env[0].config['code']), "wb") as f:
            f.write(code)
            f.close()
        with open(os.path.join(dname, 'exec.sh'), "w") as f:
            f.write(compile_script)
            f.close()
        try:
            dclient.containers.run('judge',
                volumes={dname:{'bind':'/judge', 'mode' : 'rw'}},
                remove=True
            )
        except:
            submit.status = JudgeStatus.CompilationError
            result["status"] = "fail"
        else:
            result["status"] = "success"
            with open(os.path.join(dname, env[0].config['exec_binary']), "rb") as f:
                exec_binary  = f.read()
                result["exec_binary"] = exec_binary
    return result

def check_each_test(submit, compile_result, s, dclient, test):
    env = s.query(Environment).\
        filter(Environment.id == submit.environment_id).\
        all()
    judge_result = s.query(JudgeResult).\
        filter(JudgeResult.contest_id == test.contest_id).\
        filter(JudgeResult.problem_id == test.problem_id).\
        filter(JudgeResult.test_id == test.id).\
        filter(JudgeResult.submission_id == submit.id).\
        all()
    result = JudgeStatus.WrongAnswer
    exec_script = env[0].config["exec_script"]
    exec_binary = compile_result["exec_binary"]
    with tempfile.TemporaryDirectory() as dname:
        exec_path = os.path.join(dname, env[0].config['exec_binary'])
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
                volumes={dname:{'bind':'/judge', 'mode' : 'rw'}},
                remove=True
            )
        except:
            submit.status = JudgeStatus.RuntimeError
            result = JudgeStatus.RuntimeError
        else:
            user_output = b''
            with open(os.path.join(dname, 'user.out'), "rb") as f:
                user_output = f.read()
                if user_output == test.output:
                    result = JudgeStatus.Accepted
        judge_result[0].status = result
    return result

def check_tests(db_hostname, db_port, submit, compile_result, s, dclient):
    testcases = s.query(TestCase).\
            filter(TestCase.contest_id == submit.contest_id).\
            filter(TestCase.problem_id == submit.problem_id).\
            all()
    result = JudgeStatus.Accepted
    for test in testcases:
        test_result = check_each_test(submit, compile_result,
                                        s, dclient, test)
        if test_result != JudgeStatus.Accepted:
            result = test_result
    submit.status = result
    return

def Run(db_hostname, db_port, id_body):

    id_body = json.loads(id_body)

    print("judge start with below information")
    print("contest_id : " + id_body['contest_id'])
    print("problem_id : " + id_body['problem_id'])
    print("submission_id : " + str(id_body['submission_id']))
    print("user_id : " + id_body['user_id'])

    docker_client = docker.from_env()
    configure()
    with transaction() as s:
            submission = s.query(Submission).\
                filter(Submission.contest_id == id_body['contest_id']).\
                filter(Submission.problem_id == id_body['problem_id']).\
                filter(Submission.id == id_body['submission_id']).\
                filter(Submission.user_id == id_body['user_id']).\
                all()
            
            for submit in submission:
                result = compile(db_hostname, db_port , 
                                    submit, s, docker_client)
                if result["status"] == "fail":
                    continue
                check_tests(db_hostname, db_port, submit, 
                                    result, s, docker_client)
                print('test')
                    
    print("judge end")
    pass

if __name__ == "__main__":
    pass

