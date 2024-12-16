from main.apps.nium.services.api.connectors.base import NiumAPIBaseConnector


class NiumWalletConnector(NiumAPIBaseConnector):
    def get_wallet_balance(self, wallet_hash_id: str):
        url = f"{self.get_api_url(version='v1')}/wallet/{wallet_hash_id}"
        response = self.get_request(url=url)
        return response
