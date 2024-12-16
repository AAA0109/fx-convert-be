from typing import Optional
from main.apps.account.models.company import Company
from main.apps.corpay.models.costs import TransactionCost
from main.apps.currency.models.currency import Currency


class CorpayCostService:
    company : Company

    def __init__(self, company: Company) -> None:
        self.company = company

    def get_cost(self, amount_in_usd: float, currency: Currency) -> Optional['TransactionCost']:
        return TransactionCost.get_cost(company=self.company, notional_in_usd=amount_in_usd, currency=currency)
