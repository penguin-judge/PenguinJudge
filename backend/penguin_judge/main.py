import logging
from argparse import ArgumentParser, Namespace
from os import sched_getaffinity
from typing import List

from penguin_judge import config, load_config_file


def start_api(args: Namespace, rest: List[str]) -> None:
    from uvicorn.main import main as uvicorn_main

    if args.config:
        load_config_file(args.config, "api")
    uvicorn_main([f"{__package__}.api:app"] + rest)


def start_worker(args: Namespace, rest: List[str]) -> None:
    from penguin_judge.worker import main as worker_main

    if args.config:
        load_config_file(args.config, "worker")
    max_processes = config.max_processes
    if max_processes <= 0:
        max_processes = len(sched_getaffinity(0))
    worker_main({"sqlalchemy.url": config.db_url}, max_processes)


def run_alembic(args: Namespace, rest: list[str]) -> None:
    from alembic import command
    from alembic.config import Config

    if args.config:
        load_config_file(args.config, "alembic")
    cfg = Config()
    cfg.set_main_option("script_location", "penguin_judge:alembic")
    cfg.set_main_option("sqlalchemy.url", config.db_url)

    allow_commands = ["current", "upgrade", "downgrade", "history", "revision", "heads"]
    if not rest or rest[0] not in allow_commands:
        print(f"require command: {allow_commands}")
        return
    getattr(command, rest[0])(cfg, *rest[1:])


def main() -> None:
    def add_common_args(parser: ArgumentParser) -> ArgumentParser:
        parser.add_argument("-c", "--config", help="config path")
        return parser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    api_parser = add_common_args(subparsers.add_parser("api", help="API Server"))
    api_parser.set_defaults(start=start_api)

    worker_parser = add_common_args(
        subparsers.add_parser("worker", help="Judge Worker")
    )
    worker_parser.set_defaults(start=start_worker)

    alembic_parser = add_common_args(
        subparsers.add_parser("alembic", help="Alembic Database Migration")
    )
    alembic_parser.set_defaults(start=run_alembic)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s@ %(name)s [%(levelname)s] %(funcName)s: %(message)s"
        )
    )
    logging.basicConfig(level=logging.NOTSET, handlers=[stream_handler])

    args, rest = parser.parse_known_args()
    if hasattr(args, "start"):
        args.start(args, rest)
    else:
        parser.print_help()
