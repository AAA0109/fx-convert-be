from typing import Iterable

from hdlib.DateTime.Date import Date

from main.apps.account.models import Company, Account

from main.apps.hedge.services.broker import BrokerService
from main.apps.margin.models import Deposit


class DepositService:

    def __init__(self, broker_service: BrokerService = BrokerService()):
        self._broker_service = broker_service

    def get_pending_deposits(self, company: Company, date: Date) -> float:
        broker_account = self._broker_service.get_broker_for_company(
            company=company,
            account_type=Account.AccountType.LIVE)
        total = 0.0
        for deposit in Deposit.get_pending_deposits(broker_account=broker_account):
            total += deposit.amount
        return total

