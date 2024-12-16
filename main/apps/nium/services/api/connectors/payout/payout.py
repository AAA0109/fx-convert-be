from typing import Dict, Union
from main.apps.nium.services.api.connectors.base import NiumAPIBaseConnector
from main.apps.nium.services.api.dataclasses.payout import TransferMoneyPayload


class NiumPayoutConnector(NiumAPIBaseConnector):

    def transfer_money(self, wallet_hash_id:str, data:Union[TransferMoneyPayload, Dict]):
        url = f"{self.get_api_url(version='v1', include_customer=False)}/wallet/{wallet_hash_id}/remittance"
        response = self.post_request(url, data=data)
        return response
