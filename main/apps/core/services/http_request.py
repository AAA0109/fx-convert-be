import abc
import atexit
from typing import Optional, Iterable, Tuple

import requests


# =================

class HTTPRequestService(abc.ABC):
    def make_request(self, method: str = 'post', url: str = '', data=None, headers: Optional[dict] = None,
                     files: Optional[Iterable[Tuple]] = None):
        if data is None:
            data = {}
        api = self.session if hasattr(self, 'session') else requests
        response = None
        if method == 'post':
            response = api.post(url, json=data, headers=headers, files=files)
        if method == 'get':
            response = api.get(url, params=data, headers=headers)
        if method == 'delete':
            response = api.delete(url, headers=headers)
        if method == 'put':
            response = api.put(url, json=data, headers=headers)
        if method == 'patch':
            response = api.patch(url, json=data, headers=headers)
        return response


# ============

class ApiBase:
    SESSION = None

    @classmethod
    def get_session(cls):
        if not cls.SESSION:
            cls.SESSION = requests.Session()
            atexit.register(cls.close)

        return cls.SESSION

    @classmethod
    def close(cls):
        if cls.SESSION:
            # clean up
            cls.SESSION.close()
            cls.SESSION = None

    def get(self, *args, **kwargs):
        return self.get_session().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.get_session().post(*args, **kwargs)
