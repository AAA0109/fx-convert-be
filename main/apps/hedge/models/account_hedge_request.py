from auditlog.registry import auditlog

from main.apps.currency.models import FxPair, Currency
from main.apps.hedge.support.account_hedge_interfaces import AccountHedgeResultInterface, AccountHedgeRequestInterface
from main.apps.hedge.models.company_hedge_action import CompanyHedgeAction
from main.apps.account.models import Account, AccountTypes, Company, CompanyTypes

from hdlib.DateTime.Date import Date
from typing import List, Tuple, Any, Dict, Sequence, Union, Optional

from django.db import models

import logging

logger = logging.getLogger(__name__)


class AccountHedgeRequest(models.Model, AccountHedgeRequestInterface, AccountHedgeResultInterface):
    """
    Object that lets us keep track of what changes, due to hedging, an account wanted.

    We use this for reconciliation. We aggregate orders on the company level, and then at the end of trading, have
    to go back and "fill" the account, allocating net trades back to the separate accounts.
    """

    class Meta:
        verbose_name_plural = "accounthedgerequests"
        unique_together = (("company_hedge_action", "account", "pair"),)

    class OrderStatus(models.IntegerChoices):
        OPEN = 1  # An open order (in the sense that we haven't reconciled it yet)
        CLOSED = 2  # A closed order, in the sense that we have fully reconciled it

    # ============================================================================
    #  Fields associated with the request.
    # ============================================================================

    # The company hedge action this hedge activity is associated with.
    company_hedge_action = models.ForeignKey(CompanyHedgeAction, on_delete=models.CASCADE, null=False)

    # The account this request is for.
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # The requested FX pair. Note that this should be a market traded pair.
    pair = models.ForeignKey(FxPair, on_delete=models.PROTECT, null=False)

    # The amount of FX requested.
    requested_amount = models.FloatField(null=False)

    # ============================================================================
    #  Fields to be filled during reconciliation (i.e. about how the request was serviced).
    # ============================================================================

    # The actual amount that was "filled" by the hedging, calculated from the diff between the final and original
    # account positions. Will initially be null, then will be updated.
    filled_amount = models.FloatField(null=True)

    # The average rate (price) that was achieved over the fill
    avg_price = models.FloatField(null=True)

    # Realized PnL in the quote currency (resulting from this hedge request)
    realized_pnl_quote = models.FloatField(null=True)

    # Realized PnL in the Domestic/account currency (resulting from this hedge request)
    realized_pnl_domestic = models.FloatField(null=True)

    # Commission resulting from this hedge request.
    commission = models.FloatField(null=True)

    # Counter currency commission resulting from this hedge request.
    commission_cntr = models.FloatField(null=True)

    # Status of the request (orders).
    status = models.IntegerField(null=False, default=OrderStatus.OPEN, choices=OrderStatus.choices)

    # ============================================================================
    #  AccountHedgeResultInterface.
    # ============================================================================

    def get_fx_pair(self) -> FxPair:
        return self.pair

    def get_requested_amount(self) -> float:
        return self.requested_amount

    def get_account(self) -> Account:
        return self.account

    def create_result_object(self) -> AccountHedgeResultInterface:
        """
        Create an AccountHedgeResultInterface object that can be used to report the result of the request.
        Since AccountHedgeRequest is also an AccountHedgeResultInterface, just return self.
        """
        return self

    # ============================================================================
    #  AccountHedgeResultInterface.
    # ============================================================================

    def set_filled_amount(self, filled_amount: float):
        self.filled_amount = filled_amount

    def set_avg_price(self, avg_price: float):
        self.avg_price = avg_price

    def set_commissions(self, commission: float, cntr_commission: float):
        self.commission = commission
        self.commission_cntr = cntr_commission

    def set_realized_pnl_quote(self, pnl_quote: float):
        self.realized_pnl_quote = pnl_quote

    def set_realized_pnl_domestic(self, pnl_domestic: float):
        self.realized_pnl_domestic = pnl_domestic

    def get_request(self) -> AccountHedgeRequestInterface:
        return self

    def get_filled_amount(self):
        return self.filled_amount

    def get_total_price(self):
        return self.price[0]  # Just get the amount.

    def get_pnl_quote(self) -> float:
        return self.realized_pnl_quote

    def get_pnl_domestic(self) -> float:
        return self.realized_pnl_domestic

    # ============================================================================
    #  Member functions.
    # ============================================================================

    @property
    def is_closed(self) -> bool:
        return self.status == AccountHedgeRequest.OrderStatus.CLOSED or self.requested_amount == 0

    @property
    def price(self) -> Tuple[float, Currency]:
        if not self.filled_amount or not self.avg_price:
            return 0.0, self.quote_currency

        return self.filled_amount * self.avg_price, self.quote_currency

    @property
    def quote_currency(self) -> Currency:
        return self.pair.quote_currency

    @staticmethod
    def get_hedge_request_objs(account: Optional[AccountTypes] = None,
                               company: Optional[CompanyTypes] = None,
                               company_hedge_action: Optional[CompanyHedgeAction] = None,
                               account_types: Sequence[Account.AccountType] = None,
                               start_date: Optional[Date] = None,
                               end_date: Optional[Date] = None,
                               include_start_date: bool = True) -> Sequence['AccountHedgeRequest']:
        filters = {}
        if account:
            filters["account"] = account
        if company:
            company = Company.get_company(company=company)
            filters["account__company"] = company
        if company_hedge_action:
            filters["company_hedge_action"] = company_hedge_action
        if account_types is not None and 0 < len(account_types):
            filters["account__type__in"] = account_types
        if start_date:
            filters["company_hedge_action__time__gte" if include_start_date else "company_hedge_action__time__gt"]\
                = start_date
        if end_date:
            filters["company_hedge_action__time__lte"] = end_date

        return AccountHedgeRequest.objects.filter(**filters)

    @staticmethod
    def get_hedge_requests_by_action_and_account(account: Optional[AccountTypes] = None,
                                                 company: Optional[CompanyTypes] = None,
                                                 company_hedge_action: Optional[CompanyHedgeAction] = None,
                                                 account_types: Sequence[Account.AccountType] = None,
                                                 start_date: Optional[Date] = None,
                                                 end_date: Optional[Date] = None
                                                 ) -> Dict[CompanyHedgeAction, Dict[Account, 'AccountHedgeRequest']]:
        request_objs = AccountHedgeRequest.get_hedge_request_objs(account=account,
                                                                  company=company,
                                                                  company_hedge_action=company_hedge_action,
                                                                  account_types=account_types,
                                                                  start_date=start_date,
                                                                  end_date=end_date)
        account_hedge_requests = {}
        for obj in request_objs:
            account_hedge_requests.setdefault(obj.company_hedge_action, {}).setdefault(obj.account, []).append(obj)
        return account_hedge_requests

auditlog.register(AccountHedgeRequest)
