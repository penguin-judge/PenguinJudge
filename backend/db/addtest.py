from argparse import ArgumentParser
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base
import time
from typing import Any, NamedTuple, List, Tuple, Optional
from model.model import *
from contextlib import contextmanager
from typing import Iterator
import datetime
import json

def add_test_user(s):
    test_user = User()
    test_user.id = '1'
    test_user.name = 'test'
    test_user.salt = b'1234'
    test_user.password = b'1234'
    s.add(test_user)
    
def add_test_contest(s):
    test_contest = Contest()
    test_contest.id = '1'
    test_contest.title = 'test_contest'
    test_contest.description = 'test!'
    test_contest.start_time = datetime.datetime.now()
    test_contest.end_time = datetime.datetime.now()
    s.add(test_contest)

def add_test_environment(s):
    test_environment = Environment()
    test_environment.id = 1
    test_environment.name = 'test'
    test_environment.config = json.loads('{"language" : "C", "compile_script" : "gcc -o ./a.out main.c", "srcfile_name" : "main.c", "exec_binary" : "a.out", "exec_script" : "./a.out < input.in > user.out"}')
    s.add(test_environment)

def add_test_problem(s):
    test_problem = Problem()
    test_problem.id = '1'
    test_problem.contest_id = '1'
    test_problem.title = 'test'
    test_problem.description = 'test'
    s.add(test_problem)

def add_test_testcase(s):
    test_testcase = TestCase()
    test_testcase.id = '1'
    test_testcase.contest_id = '1'
    test_testcase.problem_id = '1'
    test_testcase.input = b'1234'
    test_testcase.output = b'1234'
    s.add(test_testcase)
    test_testcase = TestCase()
    test_testcase.id = '2'
    test_testcase.contest_id = '1'
    test_testcase.problem_id = '1'
    test_testcase.input = b''
    test_testcase.output = b''
    s.add(test_testcase)

def add_test_submission(s):
    test_submission = Submission()
    test_submission.id = 1
    test_submission.contest_id = '1'
    test_submission.user_id = '1'
    test_submission.problem_id = '1'
    test_submission.code = b'int main(){}'
    test_submission.environment_id = 1
    test_submission.status = JudgeStatus.Waiting
    s.add(test_submission)

def add_judge_result(s):
    judge_result = JudgeResult()
    judge_result.contest_id = '1'
    judge_result.problem_id = '1'
    judge_result.submission_id = 1
    judge_result.test_id = '1'
    s.add(judge_result)
    judge_result = JudgeResult()
    judge_result.contest_id = '1'
    judge_result.problem_id = '1'
    judge_result.submission_id = 1
    judge_result.test_id = '2'
    s.add(judge_result)


def run_command(command : str) -> None:
    
    if command == 'None':
        configure()
    elif command == 'clear':
        configure(drop_all = true) 
    elif command == 'addtest':
        configure()
        with transaction() as s:
            add_test_user(s)
            add_test_contest(s)
            add_test_environment(s)
            add_test_problem(s)
            add_test_testcase(s)
            add_test_submission(s)
    elif command == 'reset':
        configure(drop_all = true) 
        configure()
        with transaction() as s:
            add_test_user(s)
            add_test_contest(s)
            add_test_environment(s)
            add_test_problem(s)
            add_test_testcase(s)
            add_test_submission(s)
    elif command == 'workertest':
        configure(drop_all = true) 
        configure()
        with transaction() as s:
            add_test_user(s)
            add_test_contest(s)
            add_test_environment(s)
            add_test_problem(s)
            add_test_testcase(s)
            add_test_submission(s)   
            add_judge_result(s)    
            

def get_server_option() -> Any:
    argparser = ArgumentParser()
    argparser.add_argument('-c', '--command', type=str,
                            default='None',
                            help='The command for judgeDB')
    return argparser.parse_args()

if __name__ == "__main__":
    args = get_server_option()
    print('The command is ' + args.command)
    run_command(args.command)