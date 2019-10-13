from argparse import ArgumentParser, Namespace
import datetime
import json

from penguin_judge.models import (
    configure, transaction, User, Contest, Environment,
    Problem, TestCase, Submission, JudgeResult, JudgeStatus,
    scoped_session)
from penguin_judge.main import _load_config


def add_test_user(s: scoped_session) -> None:
    test_user = User()
    test_user.id = '1'
    test_user.name = 'test'
    test_user.salt = b'1234'
    test_user.password = b'1234'
    s.add(test_user)


def add_test_contest(s: scoped_session) -> None:
    test_contest = Contest()
    test_contest.id = '1'
    test_contest.title = 'test_contest'
    test_contest.description = 'test!'
    test_contest.start_time = datetime.datetime.now()
    test_contest.end_time = datetime.datetime.now()
    s.add(test_contest)


def add_test_environment(s: scoped_session) -> None:
    test_environment = Environment()
    test_environment.id = 1
    test_environment.name = 'test'
    test_environment.config = json.loads('{"language" : "C", \
                        "compile_script" : "gcc -o ./a.out main.c", \
                        "srcfile_name" : "main.c", "exec_binary" : "a.out", \
                        "exec_script" : "./a.out"}')
    s.add(test_environment)


def add_test_problem(s: scoped_session) -> None:
    test_problem = Problem()
    test_problem.id = '1'
    test_problem.contest_id = '1'
    test_problem.title = 'test'
    test_problem.time_limit = 5
    test_problem.memory_limit = 64
    test_problem.description = 'test'
    s.add(test_problem)


def add_test_testcase(s: scoped_session) -> None:
    test_testcase = TestCase()
    test_testcase.id = '1'
    test_testcase.contest_id = '1'
    test_testcase.problem_id = '1'
    test_testcase.input = b'1234\n'
    test_testcase.output = b'1234'
    s.add(test_testcase)
    test_testcase = TestCase()
    test_testcase.id = '2'
    test_testcase.contest_id = '1'
    test_testcase.problem_id = '1'
    test_testcase.input = b'1\n'
    test_testcase.output = b'1'
    s.add(test_testcase)


def add_test_submission(s: scoped_session) -> None:
    test_submission = Submission()
    test_submission.id = 1
    test_submission.contest_id = '1'
    test_submission.user_id = '1'
    test_submission.problem_id = '1'
    test_submission.code = b'#include<stdio.h>\n#include<unistd.h>\n\
        int main(){ sleep(5);int a; scanf("%d", &a); printf("%d",a);\
        }'
    test_submission.environment_id = 1
    test_submission.status = JudgeStatus.Waiting
    s.add(test_submission)


def add_judge_result(s: scoped_session) -> None:
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


def clear_data(args: Namespace) -> None:
    config = _load_config(args, 'db')
    config['drop_all'] = True
    configure(**config)


def prejudge_data(args: Namespace) -> None:
    clear_data(args)
    with transaction() as s:
        add_test_user(s)
        add_test_contest(s)
        add_test_environment(s)
        add_test_problem(s)
        add_test_testcase(s)
        add_test_submission(s)


def worker_data(args: Namespace) -> None:
    prejudge_data(args)
    with transaction() as s:
        add_judge_result(s)


def main() -> None:
    def add_common_args(parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument('-c', '--config', required=True,
                            help='config path')
        return parser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    clear_parser = add_common_args(subparsers.add_parser(
        'clear', help='clear all data'))
    clear_parser.set_defaults(start=clear_data)

    prejudge_parser = add_common_args(subparsers.add_parser(
        'prejudge', help='set prejudge data'))
    prejudge_parser.set_defaults(start=prejudge_data)

    worker_parser = add_common_args(subparsers.add_parser(
        'worker', help='set prejudge + judge_result data'))
    worker_parser.set_defaults(start=worker_data)
    args = parser.parse_args()

    if hasattr(args, 'start'):
        args.start(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
