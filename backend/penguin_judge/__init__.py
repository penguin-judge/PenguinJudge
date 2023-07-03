import os
from configparser import DEFAULTSECT, ConfigParser

from pydantic import AnyUrl, BaseModel


class _Config(BaseModel):
    # common
    db_url: AnyUrl = "postgresql+psycopg://penguin:penguin@localhost:5432/penguin_judge"  # type: ignore
    mq_url: AnyUrl = "amqp://guest:guest@localhost:5672/"  # type: ignore

    # api
    user_judge_queue_limit: int = 10
    auth_required: bool = False

    # worker
    max_processes: int = 0
    """0=num of cpus (default: 0)."""


config = _Config()
CONFIG_KEY_MAPPING = {
    "sqlalchemy.url": "db_url",
    "mq.url": "mq_url",
}


def load_config_file(path: str, section: str) -> None:
    parser = ConfigParser()
    parser.read(path)
    if not parser.has_section(section):
        section = DEFAULTSECT
    for k, v in parser.items(section):
        if k in CONFIG_KEY_MAPPING:
            k = CONFIG_KEY_MAPPING[k]
        _update_config(k, v)
    _Config(**config.dict())  # validate


def _update_config(k: str, v: str) -> None:
    if not hasattr(config, k):
        raise ValueError(f'"{k}" is invalid config name')
    setattr(config, k, v)


def _from_env() -> None:
    for k, v in os.environ.items():
        k = k.lower()
        if not k.startswith("penguin_"):
            continue
        _update_config(k[8:], v)
    _Config(**config.dict())  # validate


_from_env()
