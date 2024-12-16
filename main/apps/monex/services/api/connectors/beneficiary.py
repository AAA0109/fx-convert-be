import logging
from typing import Optional

from main.apps.monex.services.api.dataclasses.beneficiary import (
    BeneAddPayload,
    BeneGetBankPayload,
    BeneSavePayload
)
from main.apps.monex.services.monex import MonexApi

logger = logging.getLogger(__name__)


class MonexBeneficiaryAPI(MonexApi):
    def beneficiary_add(self, company, data: Optional[BeneAddPayload] = None):
        headers = self.get_headers(company=company)
        url = f'{self.url_base}/beneficiaries/add'
        if not data:
            data = BeneAddPayload()
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data.dict())
        response = self.handle_response(response)
        return response['data']

    def beneficiary_get_bank(self, company, data: BeneGetBankPayload):
        headers = self.get_headers(company=company)
        url = f'{self.url_base}/beneficiaries/getBank'
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data.dict())
        response = self.handle_response(response)
        return response['data']

    def beneficiary_save(self, company, data: BeneSavePayload):
        headers = self.get_headers(company=company)
        url = f'{self.url_base}/beneficiaries/save'
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=data.dict())
        response = self.handle_response(response)
        return response['data']

    def beneficiary_list(self, company, limit=100000):
        headers = self.get_headers(company=company)
        url = f"{self.url_base}/beneficiaries/getList"
        payload = {
            "limit": limit,
            "entityId": company.monexcompanysettings.entity_id,
        }
        response = self.request_with_relogin(
            self.post, url, company, headers=headers, json=payload)
        response = self.handle_response(response)
        return response['data']

    def beneficiary_view(self, company, beneficiary_id: int):
        headers = self.get_headers(company=company)
        url = f"{self.url_base}/beneficiaries/view/{beneficiary_id}"
        response = self.request_with_relogin(
            self.post, url, company, headers=headers)
        response = self.handle_response(response)
        return response['data']
