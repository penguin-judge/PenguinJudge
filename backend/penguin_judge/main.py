from argparse import ArgumentParser, Namespace
from configparser import ConfigParser
from os import sched_getaffinity
from typing import Any, Mapping

from penguin_judge.models import configure, get_db_config
from penguin_judge.mq import configure as configure_mq


def _load_config(args: Namespace, name: str,
                 exclude_defaults: bool = False) -> Mapping[str, str]:
    config = ConfigParser()
    if args.config:
        config.read(args.config)
    ret = dict(config.defaults())
    if config.has_section(name):
        ret = dict(config.items(name))
    if exclude_defaults:
        for k in config.defaults().keys():
            ret.pop(k, None)
        return ret

    require_keys = ('sqlalchemy.url', 'mq.url')
    for k in require_keys:
        if k not in ret:
            raise RuntimeError('config error: {} must be specified'.format(k))

    return ret


def start_api(args: Namespace) -> None:
    from gunicorn.app.base import BaseApplication  # type: ignore
    from penguin_judge.api import app

    config = _load_config(args, 'api')
    configure_mq(**config)

    class App(BaseApplication):
        def load_config(self) -> None:
            config = _load_config(args, 'gunicorn', exclude_defaults=True)
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self) -> Any:
            # DBはプロセス単位で初期化する必要がある
            configure(**config)
            return app

    App().run()


def start_worker(args: Namespace) -> None:
    from penguin_judge.worker import main as worker_main
    config = _load_config(args, 'worker')
    configure(**config)
    configure_mq(**config)
    max_processes = int(config.get('max_processes', 0))
    if max_processes <= 0:
        max_processes = len(sched_getaffinity(0))
    worker_main(get_db_config(), max_processes)


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

    worker_parser = add_common_args(subparsers.add_parser(
        'worker', help='Judge Worker'))
    worker_parser.set_defaults(start=start_worker)

    args = parser.parse_args()
    if hasattr(args, 'start'):
        args.start(args)
    else:
        parser.print_help()
