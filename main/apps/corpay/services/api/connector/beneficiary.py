import uuid

from main.apps.corpay.services.api.connector.base import CorPayAPIBaseConnector
from main.apps.corpay.services.api.dataclasses.beneficiary import BeneficiaryRulesQueryParams, BeneficiaryRequestBody, \
    BeneficiaryListQueryParams, BankSearchParams, IbanValidationRequestBody


class CorPayAPIBeneficiaryConnector(CorPayAPIBaseConnector):
    def beneficiary_rules(self, client_code: int, access_code: str, data: BeneficiaryRulesQueryParams):
        url = f"{self.api_url}/api/{client_code}/0/template-guide"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']

    def upsert_beneficiary(self, client_code: int, access_code: str, client_integration_id: str,
                           data: BeneficiaryRequestBody):
        url = f"{self.api_url}/api/{client_code}/0/templates/{client_integration_id}"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']

    def get_beneficiary(self, client_code: int, access_code: str, client_integration_id: str):
        url = f"{self.api_url}/api/{client_code}/0/templates/{client_integration_id}"
        response = self.get_request(url=url, access_code=access_code)
        return response['content']

    def delete_beneficiary(self, client_code: int, access_code: str, client_integration_id: str):
        url = f"{self.api_url}/api/{client_code}/0/templates/{client_integration_id}"
        response = self.delete_request(url=url, access_code=access_code)
        return response['content']

    def list_beneficiary(self, client_code, access_code, data: BeneficiaryListQueryParams = None):
        url = f"{self.api_url}/api/{client_code}/0/benes"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']

    def list_bank(self, access_code: str, data: BankSearchParams):
        url = f"{self.api_url}/api/banks"
        response = self.get_request(url=url, access_code=access_code, data=data)
        return response['content']

    def iban_validation(self, access_code: str, data: IbanValidationRequestBody):
        url = f"{self.api_url}/api/ibanvalidation"
        response = self.post_request(url=url, access_code=access_code, data=data)
        return response['content']
