import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests
from django.conf import settings


class OEMSBaseAPIConnector(ABC):
    """ OEMS API Connectors - this class is responsible for interacting with the OEMS API """

    class Meta:
        abstract = True

    API_PREFIX = 'api/v1'
    AUTH = (settings.OEMS_USER, settings.OEMS_PASSWORD)

    # ============================================================================
    #  Helper functions.
    # ============================================================================

    def _request(self, path: str = "/", method: str = 'get', data: Optional[dict] = None):
        if data is None:
            data = {}
        path = self._get_request_url(path)
        logging.info(f"oems_connector: Sending request to {path}")
        if method == 'get':
            response = requests.get(path, auth=self.AUTH, verify=False)
        elif method == 'post':
            logging.info(f"oems_connector: payload {data}")
            response = requests.post(path, auth=self.AUTH, json=data, verify=False)
        else:
            raise RuntimeError("method is neither 'get' nor 'post'")
        # Check for errors in the response.
        if response.status_code == 403:
            raise RuntimeError(f"response status was 403, reason: {response.reason}")
        # If there were no errors, convert response to a json.
        try:
            logging.info(f"oems_connector: response status code {response.status_code}")
            logging.info(f"oems_connector: response content {response.content}")
            return response.json()
        except Exception as ex:
            raise RuntimeError(f"response could not be converted to json, status code was "
                               f"{response.status_code}: {ex}")

    @abstractmethod
    def _get_request_url(self, path: str) -> str:
        raise NotImplementedError
