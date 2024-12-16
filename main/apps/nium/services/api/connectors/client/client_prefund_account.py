from typing import Dict, Union
from main.apps.nium.services.api.connectors.base import NiumAPIBaseConnector
from main.apps.nium.services.api.dataclasses.client import ClientPrefundPayload


class NiumPrefundAccountConnector(NiumAPIBaseConnector):

    def client_prefund_request(self, data:Union[ClientPrefundPayload, Dict]):
        url = f"{self.get_api_url(version='v1', include_customer=False)}/prefund"
        response = self.post_request(url, data=data)
        return response
