import datetime
import json
from base64 import b64encode
from enum import Enum
from typing import Any


def to_fastapi_response_compatible_value(o: Any) -> str | int | float | bool | None:
    if isinstance(o, datetime.datetime):
        return o.astimezone(tz=datetime.timezone.utc).isoformat()
    if isinstance(o, datetime.timedelta):
        return o.total_seconds()
    if isinstance(o, bytes):
        return b64encode(o).decode("ascii")
    if isinstance(o, Enum):
        return o.name
    assert o is None or isinstance(o, (str, int, float, bool))
    return o


class _JsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        return to_fastapi_response_compatible_value(o)


def json_dumps(o: dict[str, Any] | list[Any]) -> str:
    if isinstance(o, dict):
        o = {k: v for k, v in o.items() if not k.startswith("_")}
    return json.dumps(o, cls=_JsonEncoder, separators=(",", ":"))


def pagination_header(count: int, page: int, per_page: int) -> dict[str, int]:
    return {
        "X-Page": page,
        "X-Per-Page": per_page,
        "X-Total": count,
        "X-Total-Pages": (count + (per_page - 1)) // per_page,
    }
