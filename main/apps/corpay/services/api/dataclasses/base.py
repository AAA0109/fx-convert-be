import json
from dataclasses import asdict
import datetime
from uuid import UUID


class JsonDictMixin:
    def dict(self):
        output = {}
        for k, v in asdict(self).items():
            if v is not None:
                if isinstance(v, set):
                    v = list(v)
                elif isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
                    v = v.isoformat()
                elif isinstance(v, UUID):
                    v = str(v)
                output[k] = v
        return output

    def json(self):
        return json.dumps(self.dict())
