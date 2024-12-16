from typing import Dict, Union
from main.apps.nium.services.api.connectors.base import NiumAPIBaseConnector
from main.apps.nium.services.api.dataclasses.testing import SimulateRcvTrxPayload


class NiumTestingPayInConnector(NiumAPIBaseConnector):

    def simulate_receiving_transaction(self, data:Union[SimulateRcvTrxPayload, Dict]):
        base_api_url = self.get_api_url(version='v1',
                                        include_customer=False).split('v1')
        url = f"{base_api_url[0]}v1/inward/payment/manual"
        response = self.post_request(url, data=data)
        return response
