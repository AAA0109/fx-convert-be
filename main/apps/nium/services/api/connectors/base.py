import logging
from typing import Optional, Iterable, Tuple, Union, Dict

from django.conf import settings

from main.apps.core.services.http_request import HTTPRequestService
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin
from main.apps.nium.services.api.exceptions import BadRequest, Unauthorized, Forbidden, NotFound, MethodNotAllowed, \
    TooManyRequests, InternalServerError, ServiceUnavailable

logger = logging.getLogger(__name__)


class NiumAPIConfig:
    _instance = None
    customer_hash_id: str = ''

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NiumAPIConfig, cls).__new__(cls)
        return cls._instance

    def set_customer_hash_id(self, customer_hash_id: str):
        self.customer_hash_id = customer_hash_id

    def get_customer_hash_id(self):
        return self.customer_hash_id


class NiumAPIBaseConnector(HTTPRequestService):
    version: str = 'v2'
    customer_hash_id: str = ''
    request_id: str = None

    def __init__(self):
        self.config = NiumAPIConfig()

    def set_request_id(self, request_id: str) -> None:
        self.request_id = request_id

    def unset_request_id(self) -> None:
        self.request_id = None

    def get_api_url(self, version=None, include_customer=True):
        api_version = self.version
        if version is not None:
            api_version = version
        url = f'{settings.NIUM_API_BASE}/{api_version}/client/{settings.NIUM_CLIENT_ID}'
        if include_customer:
            url += f'/customer/{self.config.customer_hash_id}'
        return url

    def get_headers(self, ):
        header = {
            "accept": "application/json",
            "x-api-key": settings.NIUM_API_KEY,
        }
        if self.request_id:
            header['x-request-id'] = self.request_id
        return header

    def make_request(self, method: str = 'post', url: str = '', data: Optional[Union[JsonDictMixin, Dict]] = None,
                     headers: Optional[dict] = None,
                     files: Optional[Iterable[Tuple]] = None):
        if data is None:
            data = {}
        else:
            if not isinstance(data, dict):
                data = data.dict()
        logger.debug("Nium Connector making request to: %s", url)
        logger.debug("headers: %s", headers)
        logger.debug("payload: %s", data)
        method = method.lower()
        return super().make_request(method=method, url=url, data=data, headers=headers)

    def post_request(self, url: str, data: Optional[Union[JsonDictMixin, Dict]] = None,
                     files: Optional[Iterable[Tuple]] = None):
        payload = None
        if data is not None:
            if not isinstance(data, dict):
                payload = data.dict()
            else:
                payload = data

        headers = self.get_headers()
        logger.debug(f"URL: POST {url}")
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")
        response = self.make_request(method='post', url=url, data=payload, headers=headers, files=files)
        response = self.handle_response(response)
        return response

    def get_request(self, url: str, params: Optional[Union[JsonDictMixin, Dict]] = None):
        headers = self.get_headers()
        logger.debug(f"URL: GET {url}")
        logger.debug(f"Params: {params}")
        logger.debug(f"Headers: {headers}")
        response = self.make_request(method='get', url=url, data=params, headers=headers)
        response = self.handle_response(response)
        return response

    def put_request(self, url: str, data: Optional[Union[JsonDictMixin, Dict]] = None):
        payload = None
        if data is not None:
            if not isinstance(data, dict):
                payload = data.dict()
            else:
                payload = data

        headers = self.get_headers()
        logger.debug(f"URL: PUT {url}")
        logger.debug(f"Data: {data}")
        logger.debug(f"Headers: {headers}")
        response = self.make_request(method='put', url=url, data=payload, headers=headers)
        response = self.handle_response(response)
        return response

    def patch_request(self, url: str, data: Optional[Union[JsonDictMixin, Dict]] = None):
        payload = None
        if data is not None:
            if not isinstance(data, dict):
                payload = data.dict()
            else:
                payload = data

        headers = self.get_headers()
        logger.debug(f"URL: PATCH {url}")
        logger.debug(f"Data: {data}")
        logger.debug(f"Headers: {headers}")
        response = self.make_request(method='patch', url=url, data=payload, headers=headers)
        response = self.handle_response(response)
        return response

    def delete_request(self, url: str):
        headers = self.get_headers()
        logger.debug(f"URL: DELETE {url}")
        logger.debug(f"Headers: {headers}")
        response = self.make_request(method='delete', url=url, headers=headers)
        response = self.handle_response(response)
        return response

    def handle_response(self, response):
        response_json = response.json()
        logger.debug(f"Response: {response_json}")

        if response.status_code in [200, 201]:
            return response_json
        if response.status_code == 400:
            raise BadRequest('Bad Request', response_json)
        if response.status_code == 401:
            raise Unauthorized('Unauthorized', response_json)
        if response.status_code == 403:
            raise Forbidden('Forbidden', response_json)
        if response.status_code == 404:
            raise NotFound('Not Found', response_json)
        if response.status_code == 405:
            raise MethodNotAllowed('Method Not Allowed', response_json)
        if response.status_code == 429:
            raise TooManyRequests('Too Many Requests', response_json)
        if response.status_code == 500:
            raise InternalServerError('Internal Server Error', response_json)
        if response.status_code == 503:
            raise ServiceUnavailable('Service Unavailable', response_json)
