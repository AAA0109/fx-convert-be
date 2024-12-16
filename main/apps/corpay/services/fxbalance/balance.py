import logging
from abc import ABC

import dateutil

from main.apps.account.models import Company
from main.apps.corpay.models import FXBalance
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams
from main.apps.corpay.services.corpay import CorPayService
from main.apps.currency.models import Currency

logger = logging.getLogger(__name__)


class CorPayFXBalanceDraftService(ABC):
    """
    Service to create a fxbalance object to keep the balance updated while
    the service got processed definitively.
    """

    def __init__(self):
        self.corpay_service = CorPayService()

    def create(self, company: Company, instruct_deal: dict):
        self.corpay_service.init_company(company)
        logger.debug(f"Getting FXBalance accounts for company - {company.name} - ID: {company.pk}")

        # fetch company accounts and balance
        params = ViewFXBalanceAccountsParams(includeBalance=True)
        response = self.corpay_service.list_fx_balance_accounts(params)
        company_accounts = [
            {'account_number': o['id'], 'balance': o['availableBalance']}
            for o in response['items']
        ]

        # look if the beneficiary is in the account list and create the credit record
        beneficiary_account = [
            item for item in company_accounts
            if item['account_number'] == instruct_deal['payments'][0]['beneId']
        ]
        if beneficiary_account:
            logger.debug(f"Create record for the beneficiary account for company - {company.name} - ID: {company.pk} "
                        f"acc: {beneficiary_account[0]['account_number']}")
            record = FXBalance(
                company=company,
                account_number=beneficiary_account[0]['account_number'],
                order_number=instruct_deal['ordNum'],
                date=dateutil.parser.parse(instruct_deal['valueDate']),
                currency=Currency.get_currency(instruct_deal['payments'][0]['currency']),
                amount=instruct_deal['payments'][0]['amount'],
                credit_amount=instruct_deal['payments'][0]['amount'],
                debit_amount=0,
                is_posted=False,
                status=FXBalance.FXBalanceStatus.PROCESSING
            )
            record.balance = beneficiary_account[0]['balance'] + record.amount
            record.save()

        # look if the settlement is in the account list and create the debit record
        settlement_account = [
            item for item in company_accounts
            if item['account_number'] == instruct_deal['settlements'][0]['accountId']
        ]
        if settlement_account:
            logger.debug(f"Create record for the settlement account for company - {company.name} - ID: {company.pk} "
                        f"acc: {settlement_account[0]['account_number']}")
            record = FXBalance(
                company=company,
                account_number=settlement_account[0]['account_number'],
                order_number=instruct_deal['ordNum'],
                date=dateutil.parser.parse(instruct_deal['valueDate']),
                currency=Currency.get_currency(instruct_deal['settlements'][0]['currency']),
                amount=instruct_deal['settlements'][0]['amount'] * -1,
                debit_amount=instruct_deal['settlements'][0]['amount'] * -1,
                credit_amount=0,
                is_posted=False,
                status=FXBalance.FXBalanceStatus.PROCESSING
            )
            record.balance = settlement_account[0]['balance'] + record.amount
            record.save()
