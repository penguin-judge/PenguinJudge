from typing import Optional

from pika import URLParameters  # type: ignore

_mq_url: Optional[str] = None


def configure(**kwargs: str) -> None:
    global _mq_url
    _mq_url = kwargs['mq.url']


def get_mq_conn_params() -> URLParameters:
    return URLParameters(_mq_url)
