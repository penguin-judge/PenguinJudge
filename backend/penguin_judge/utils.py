from base64 import b64encode
import datetime
from enum import Enum
from typing import Any, Union
import json


class _JsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Union[str, float]:
        if isinstance(o, datetime.datetime):
            return o.astimezone(tz=datetime.timezone.utc).isoformat()
        if isinstance(o, datetime.timedelta):
            return o.total_seconds()
        if isinstance(o, bytes):
            return b64encode(o).decode('ascii')
        if isinstance(o, Enum):
            return o.name
        return super().default(o)


def json_dumps(o: Union[dict, list]) -> str:
    if isinstance(o, dict):
        o = {k: v for k, v in o.items() if not k.startswith('_')}
    return json.dumps(o, cls=_JsonEncoder, separators=(',', ':'))


def pagination_header(count: int, page: int, per_page: int) -> dict:
    return {
        'X-Page': page,
        'X-Per-Page': per_page,
        'X-Total': count,
        'X-Total-Pages': (count + (per_page - 1)) // per_page,
    }
