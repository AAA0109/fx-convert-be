from abc import ABC

import logging
from typing import Optional

from django.core.exceptions import ValidationError

from main.apps.account.models import Company
from main.apps.corpay.services.api.dataclasses.settlement_accounts import CreateFXBalanceAccountsBody
from main.apps.corpay.services.corpay import CorPayService

logger = logging.getLogger(__name__)


class CorPayFxBalanceAccountCreator(ABC):
    def __init__(self):
        self.corpay_service = CorPayService()

    def create(self, company: Company, currencies: list, account: Optional[str] = None):
        if len(currencies) == 0:
            raise ValidationError("No currencies provided")
        self.corpay_service.init_company(company)
        data = CreateFXBalanceAccountsBody(
            currencies=currencies,
            account=account
        )
        logger.debug(f"Creating {','.join(map(str, currencies))} FX Balance accounts for Company {company.id}")
        response = self.corpay_service.create_fx_balance_accounts(data)
        logger.debug(response)


