from argparse import ArgumentParser, Namespace
import json
from typing import Dict, Union

import pika

from penguin_judge.main import _load_config
from penguin_judge.mq import configure, get_mq_conn_params


# test data in add_testdata_to_db.py
submission_data: Dict[str, Union[str, int]]
submission_data = {}
submission_data['contest_id'] = '1'
submission_data['problem_id'] = '1'
submission_data['submission_id'] = 1
submission_data['user_id'] = '1'


def send_data_to_queue(args: Namespace, queue_name: str) -> None:
    config = _load_config(args, 'db')
    configure(**config)
    connection = pika.BlockingConnection(get_mq_conn_params())
    channel = connection.channel()
    channel.queue_declare(queue=queue_name)
    channel.basic_publish(exchange='', routing_key=queue_name,
                          body=json.dumps(submission_data))


def submit_queue(args: Namespace) -> None:
    send_data_to_queue(args, 'judge_queue')


def worker_queue(args: Namespace) -> None:
    send_data_to_queue(args, 'worker_queue')


def main() -> None:
    def add_common_args(parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument('-c', '--config', required=True,
                            help='config path')
        return parser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    submit_parser = add_common_args(subparsers.add_parser(
        'submit', help='send submit to judge_queue'))
    submit_parser.set_defaults(start=submit_queue)

    worker_parser = add_common_args(subparsers.add_parser(
        'worker', help='send judge to worker_queue'))
    worker_parser.set_defaults(start=worker_queue)
    args = parser.parse_args()

    if hasattr(args, 'start'):
        args.start(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
