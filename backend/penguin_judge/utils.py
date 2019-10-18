from base64 import b64encode
import datetime
from enum import Enum
from typing import Any, Union
import json


class _JsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> str:
        print(type(o), o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.astimezone(tz=datetime.timezone.utc).isoformat()
        if isinstance(o, bytes):
            return b64encode(o).decode('ascii')
        if isinstance(o, Enum):
            return o.name
        return super().default(o)


def json_dumps(o: Union[dict, list]) -> str:
    return json.dumps(o, cls=_JsonEncoder, separators=(',', ':'))
