import urllib.parse
from django.conf import settings


def get_frontend_url(path: str, **query_params):
    url = f"{settings.FRONTEND_URL}/{path}"

    if not bool(query_params):
        return url

    return url + "?" + urllib.parse.urlencode(query_params)
