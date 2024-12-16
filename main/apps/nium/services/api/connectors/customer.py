from typing import Optional

from main.apps.nium.services.api.connectors.base import NiumAPIBaseConnector
from main.apps.nium.services.api.dataclasses.customer import ListCustomersParams


class NiumCustomerConnector(NiumAPIBaseConnector):
    def list_customer(self, data: Optional[ListCustomersParams] = None):
        url = f"{self.get_api_url(version='v3', include_customer=False)}/customers"
        response = self.get_request(url, params=data)
        return response
