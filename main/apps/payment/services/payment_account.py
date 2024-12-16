from typing import List, Optional
from main.apps.account.models.company import Company
from main.apps.settlement.models.beneficiary import Beneficiary
from main.apps.settlement.models.wallet import Wallet


class PaymentAccountMethodProvider:
    payment_payloads:List[dict]
    is_raw_data:bool = False
    wallet_accounts: List[Wallet]
    beneficiary_accounts: List[Beneficiary]
    WALLET_METHOD_KEY:str = 'method'
    BENEFICIARY_METHOD_KEY:str = 'settlement_methods'

    def __init__(self, company:Company, payment_payloads:List[dict], is_raw_data:bool = False) -> None:
        self.payment_payloads = payment_payloads
        self.is_raw_data = is_raw_data
        accounts = self.__get_account_ids()

        self.wallet_accounts = Wallet.objects.filter(company=company, wallet_id__in=accounts)\
            .values('wallet_id', self.WALLET_METHOD_KEY)
        self.beneficiary_accounts = Beneficiary.objects.filter(company=company, beneficiary_id__in=accounts)\
            .values('beneficiary_id', self.BENEFICIARY_METHOD_KEY)

    def __get_account_ids(self):
        accounts = set()
        if self.is_raw_data:
            for item in self.payment_payloads:
                accounts.add(item['destination'])
                accounts.add(item['origin'])
            return list(accounts)

        for item in self.payment_payloads:
            accounts.add(item['destination_account_id'])
            accounts.add(item['origin_account_id'])
        return list(accounts)

    def get_delivery_method(self, account_id:str) -> Optional[str]:
        account = self.__find_method_in_wallet_accounts(account_id=account_id)
        if account:
            return account[self.WALLET_METHOD_KEY]
        account = self.__find_method_in_beneficiary_accounts(account_id=account_id)
        if account:
            return account[self.BENEFICIARY_METHOD_KEY]
        return None

    def __find_method_in_wallet_accounts(self, account_id:str) -> Optional[dict]:
        found_item = next((item for item in self.wallet_accounts if item['wallet_id'] == account_id), None)
        if found_item:
            return found_item
        return None

    def __find_method_in_beneficiary_accounts(self, account_id:str) -> Optional[dict]:
        found_item = next((item for item in self.beneficiary_accounts if item['beneficiary_id'] == account_id), None)
        if found_item:
            return found_item
        return None
