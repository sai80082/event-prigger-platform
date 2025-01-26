import json
import logging
from typing import List
from datetime import datetime
from app.models import EventLog
from app.schemas import EventLogResponse

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def serialize_logs(logs: List[EventLog]) -> str:
    return json.dumps(
        [EventLogResponse.from_orm(log).model_dump() for log in logs],
        cls=DateTimeEncoder,
    )


def deserialize_logs(logs_str: str) -> List[EventLogResponse]:
    def datetime_parser(dct):
        for k, v in dct.items():
            if isinstance(v, str):
                try:
                    dct[k] = datetime.fromisoformat(v)
                except ValueError:
                    pass
        return dct

    return [
        EventLogResponse(**log)
        for log in json.loads(logs_str, object_hook=datetime_parser)
    ]
