from typing import Dict, Optional, Union
from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin

from main.apps.nium.services.api.connectors.base import NiumAPIBaseConnector
from main.apps.nium.services.api.dataclasses.beneficiary import BeneficiaryValidationSchemaParams, \
    ListBeneficiaryParams


class NiumBeneficiaryConnector(NiumAPIBaseConnector):
    def get_beneficiary_validation_schema(self, currency: str, data: BeneficiaryValidationSchemaParams):
        url = f"{self.get_api_url()}/currency/{currency}/validationSchemas"
        response = self.get_request(url=url, params=data)
        return response

    def add_beneficiary(self, data: Union[JsonDictMixin, Dict]):
        url = f"{self.get_api_url()}/beneficiaries"
        response = self.post_request(url=url, data=data)
        return response

    def update_beneficiary(self, beneficiary_id: str, data: Dict):
        url = f"{self.get_api_url()}/beneficiaries/{beneficiary_id}"
        response = self.put_request(url=url, data=data)
        return response

    def delete_beneficiary(self, beneficiary_id: str):
        url = f"{self.get_api_url(version='v1')}/beneficiaries/{beneficiary_id}"
        response = self.delete_request(url=url)
        return response

    def list_beneficiaries(self, params: Optional[ListBeneficiaryParams] = None):
        url = f"{self.get_api_url()}/beneficiaries"
        response = self.get_request(url=url, params=params)
        return response

    def get_beneficiary(self, beneficiary_id: str):
        url = f"{self.get_api_url()}/beneficiaries/{beneficiary_id}"
        response = self.get_request(url=url)
        return response
