import json
import logging
from abc import ABC

from main.apps.account.models import Company
from main.apps.corpay.models import CorpaySettings, Beneficiary
from main.apps.corpay.services.api.dataclasses.beneficiary import BeneficiaryListQueryParams
from main.apps.corpay.services.corpay import CorPayService
from main.apps.currency.models import Currency

logger = logging.getLogger(__name__)


class CorPayBeneficiaryDataService(ABC):
    def __init__(self):
        self.corpay_service = CorPayService()
        self.currencies = {c.mnemonic: c for c in Currency.get_currencies()}

    def execute(self, company_id=None):
        credentials = CorpaySettings.objects.all()
        company_ids = [credential.company.pk for credential in credentials]
        companies = Company.objects.filter(pk__in=company_ids)
        if company_id:
            companies = companies.filter(pk=company_id)

        for company in companies:
            try:
                self.handle_single(company)
            except Exception as e:
                logger.exception(e)

    def handle_single(self, company: Company):
        self.corpay_service.init_company(company)
        logger.debug(f"Getting beneficiary data for company - {company.name} - ID: {company.pk}")
        params = BeneficiaryListQueryParams()
        response = self.corpay_service.list_beneficiary(params)
        logger.info(json.dumps(response, indent=2))
