from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams, \
    FxBalanceHistoryParams, CreateFXBalanceAccountsBody


class CorPayAPISettlementAccountConnector(CorPayAPIBaseConnector):
    def settlement_accounts(self, client_code: int, access_code: str):
        url = f"{self.api_url}/api/{client_code}/0/settlement-accounts"
        response = self.get_request(url=url, access_code=access_code)
        return response['content']

    def fx_balance_accounts(self, client_code: int, access_code: str, data: ViewFXBalanceAccountsParams = None):
        url = f"{self.api_url}/api/{client_code}/0/payment-link-balance-accounts"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']

    def fx_balance_history(self, client_code: int, access_code: str, fx_balance_id: str, data: FxBalanceHistoryParams):
        url = f"{self.api_url}/api/{client_code}/0/link-balance-accounts/{fx_balance_id}/history"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']

    def create_fx_balance_accounts(self, client_code: int, access_code: str, data: CreateFXBalanceAccountsBody = None):
        url = f"{self.api_url}/api/{client_code}/0/link-balance-accounts"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']
