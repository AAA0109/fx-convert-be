from django.conf import settings
import logging
from typing import Optional, Iterable, Tuple

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, JSONDecodeError

from urllib3.util.retry import Retry

from main.apps.core.services.http_request import HTTPRequestService
from main.apps.corpay.decorators.api_logging import log_api
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin
from main.apps.corpay.services.api.dataclasses.beneficiary import BeneficiaryListQueryParams
from main.apps.corpay.services.api.exceptions import BadRequest, Forbidden, NotFound, Gone, InternalServerError

logger = logging.getLogger(__name__)


class CorPayAPIBaseConnector(HTTPRequestService):
    def __init__(self, retries=1):
        self.api_url = settings.CORPAY_API_URL
        self.session = requests.Session()

        retry_strategy = Retry(
            total=retries,  # Total number of retries to allow
            status_forcelist=[429, 500, 502, 503, 504],  # A set of HTTP status codes that we want to retry
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],  # Allow retries on these methods
            backoff_factor=1,  # Backoff factor to apply between attempts
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount(self.api_url, adapter)


    def get_headers(self, access_code: str):
        return {
            'Content-Type': 'application/json',
            'CMG-AccessToken': access_code
        }

    @staticmethod
    def handle_response(response):
        try:
            response_json = response.json()
            logger.debug(f"Response: {response_json}")

            if 'errors' in response_json:
                for error in response_json['errors']:
                    if error['key'] == 'QUOTE_EXPIRED':
                        raise Gone(response_json)
            if response.status_code in [200, 201]:
                return response_json
            if response.status_code == 400:
                raise BadRequest(response_json)
            if response.status_code == 401:
                raise Forbidden(response_json)
            if response.status_code == 403:
                raise Forbidden(response_json)
            if response.status_code == 404:
                raise NotFound("Path not found")
            if response.status_code == 410:
                raise Gone(response_json)
            if response.status_code == 500:
                raise InternalServerError(response_json)
        except JSONDecodeError as e:
            logger.error(f"Unable to decode json on this response: {response.content}")
            raise InternalServerError(response)

    def make_request(self, method: str = 'post', url: str = '', data: dict = {}, headers: Optional[dict] = None,
                     files=Optional[Iterable[Tuple]]):
        logger.debug("CorPay Connector making request to: %s", url)
        logger.debug("headers: %s", headers)
        logger.debug("payload: %s", data)
        method = method.lower()
        return super().make_request(method=method, url=url, data=data, headers=headers)

    @log_api(method='post')
    def post_request(self, url: str, access_code: str, data: Optional[JsonDictMixin] = None,
                     files: Optional[Iterable[Tuple]] = None):
        payload = None
        if data is not None:
            payload = data.dict()

        headers = self.get_headers(access_code=access_code)
        logger.debug(f"URL: POST {url}")
        logger.debug(f"Payload: {payload}")
        logger.debug(f"Headers: {headers}")
        response = self.make_request(method='post', url=url, data=payload, headers=headers, files=files)
        response = self.handle_response(response)
        return response

    @log_api(method='get')
    def get_request(self, url: str, access_code: str, data: Optional[JsonDictMixin] = None):
        params = None
        if data is not None:
            params = data.dict()
            # TODO: Need to find a better way to implement this
            if isinstance(data, BeneficiaryListQueryParams):
                if data.q is not None:
                    q = data.q.dict()
                    params['q'] = q
        headers = self.get_headers(access_code=access_code)
        response = self.make_request(method='get', url=url, data=params, headers=headers)
        response = self.handle_response(response)
        logger.debug("API Response:")
        logger.debug(response)
        return response

    @log_api(method='delete')
    def delete_request(self, url: str, access_code: str):
        headers = self.get_headers(access_code=access_code)
        response = self.make_request(method='delete', url=url, headers=headers)
        response = self.handle_response(response)
        return response
