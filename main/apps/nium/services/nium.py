from abc import ABC, abstractmethod
from typing import Optional, Dict, Union

from main.apps.account.models import Company
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin
from main.apps.nium.services.api.connectors.base import NiumAPIConfig
from main.apps.nium.services.api.connectors.beneficiary import NiumBeneficiaryConnector
from main.apps.nium.services.api.connectors.customer import NiumCustomerConnector
from main.apps.nium.services.api.connectors.wallet import NiumWalletConnector
from main.apps.nium.services.api.dataclasses.beneficiary import BeneficiaryValidationSchemaParams, \
    ListBeneficiaryParams
from main.apps.nium.services.api.dataclasses.customer import ListCustomersParams


class NiumAPIInterface(ABC):

    @abstractmethod
    def get_beneficiary_validation_schema(self, currency: str,
                                          data: Optional[BeneficiaryValidationSchemaParams] = None):
        raise NotImplementedError


class NiumService(NiumAPIInterface):
    def __init__(self):
        self._connector = {
            'beneficiary': NiumBeneficiaryConnector(),
            'customer': NiumCustomerConnector(),
            'wallet': NiumWalletConnector()
        }

    def init_company(self, company: Company):
        config = NiumAPIConfig()
        config.set_customer_hash_id(company.niumsettings.customer_hash_id)

    def get_beneficiary_validation_schema(self, currency: str,
                                          data: Optional[BeneficiaryValidationSchemaParams] = None):
        return self._connector['beneficiary'].get_beneficiary_validation_schema(currency=currency, data=data)

    def add_beneficiary(self, data: Union[JsonDictMixin, Dict]):
        return self._connector['beneficiary'].add_beneficiary(data)

    def update_beneficiary(self, beneficiary_id: str, data: Dict):
        return self._connector['beneficiary'].update_beneficiary(beneficiary_id, data)

    def delete_beneficiary(self, beneficiary_id: str):
        return self._connector['beneficiary'].delete_beneficiary(beneficiary_id)

    def list_beneficiary(self, params: Optional[ListBeneficiaryParams] = None):
        return self._connector['beneficiary'].list_beneficiaries(params)

    def get_beneficiary(self, beneficiary_id: str):
        return self._connector['beneficiary'].get_beneficiary(beneficiary_id)

    def list_customers(self, params: Optional[ListCustomersParams] = None):
        return self._connector['customer'].list_customer(params)

    def get_wallet_balance(self, wallet_hash_id: str):
        return self._connector['wallet'].get_wallet_balance(wallet_hash_id)
