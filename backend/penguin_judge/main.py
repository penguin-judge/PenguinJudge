from argparse import ArgumentParser, Namespace
from configparser import ConfigParser
from typing import Mapping

from penguin_judge.models import configure
from penguin_judge.mq import configure as configure_mq


def _load_config(args: Namespace, name: str) -> Mapping[str, str]:
    config = ConfigParser()
    if args.config:
        config.read(args.config)
    ret = config.defaults()
    if config.has_section(name):
        ret = dict(config.items(name))

    require_keys = ('sqlalchemy.url', 'mq.url')
    for k in require_keys:
        if k not in ret:
            raise RuntimeError('config error: {} must be specified'.format(k))

    return ret


def start_api(args: Namespace) -> None:
    from penguin_judge.api import app
    config = _load_config(args, 'api')
    configure(**config)
    configure_mq(**config)
    app.run()


def start_db_server(args: Namespace) -> None:
    from penguin_judge.db_server import main as db_main
    config = _load_config(args, 'db')
    configure(**config)
    configure_mq(**config)
    db_main()


def start_worker(args: Namespace) -> None:
    from penguin_judge.worker import main as worker_main
    config = _load_config(args, 'worker')
    configure(**config)
    configure_mq(**config)
    max_processes = int(config.get('max_processes', '1'))
    worker_main(max_processes)


def main() -> None:
    def add_common_args(parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument('-c', '--config', required=True,
                            help='config path')
        return parser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    api_parser = add_common_args(subparsers.add_parser(
        'api', help='API Server'))
    api_parser.set_defaults(start=start_api)

    db_server_parser = add_common_args(subparsers.add_parser(
        'db-server', help='DB Server'))
    db_server_parser.set_defaults(start=start_db_server)

    worker_parser = add_common_args(subparsers.add_parser(
        'worker', help='Judge Worker'))
    worker_parser.set_defaults(start=start_worker)

    args = parser.parse_args()
    if hasattr(args, 'start'):
        args.start(args)
    else:
        parser.print_help()
