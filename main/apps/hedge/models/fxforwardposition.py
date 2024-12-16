from auditlog.registry import auditlog
from django.db import models
from django.db.models import Q, QuerySet
from django_extensions.db.models import TimeStampedModel

from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util import SpotFxCache

from main.apps.account.models import CashFlow, Account, AccountTypes
from main.apps.account.models.company import Company, CompanyTypes
from main.apps.currency.models.fxpair import FxPair, FxPairTypes
from hdlib.Instrument.FxForward import FxForwardInstrument

from typing import List, Dict, Sequence, Iterable, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


# ==================
# Type definitions
# ==================

class FxForwardPosition(TimeStampedModel, FxForwardInstrument):
    """
    Represents a Forward Fx position associated with an account.
    """

    class Meta:
        verbose_name_plural = "FX Forward Positions"
        unique_together = (("cashflow", "fxpair", "amount", "delivery_time", "enter_time"),)

    # The account that the forward is in.
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # Optionally, a cashflow that is specifically associated with this forward.
    cashflow = models.ForeignKey(CashFlow, on_delete=models.CASCADE, null=True)

    # The FX pair that the forward is on.
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, related_name='forwardfxpair', null=False)

    # Amount of this fx pair which defines the position (also = total price in the base currency)
    amount = models.FloatField(null=False)

    # Counter amount of this fx pair
    cntr_amount = models.FloatField(null=True)

    # Time at which the exchange of currency will occur.
    delivery_time = models.DateTimeField(null=False)

    # The time at which the forward was purchased.
    enter_time = models.DateTimeField(null=False)

    # The initial spot price of the forward (unit price, not price of the total position).
    # NOTE(Nate): Should be null=False, but we will have to transition into this.
    initial_spot_price = models.FloatField(null=True)

    # The forward (rate) price of the position (unit price, not price of the total position).
    forward_price = models.FloatField(null=False)

    # NOTE: The un-wind prices should be filled in if either the position is unwound, or the position matures, and the
    # transaction occurs. In this (second) case, the unwind_price should be the spot price, and the unwind time should
    # be the delivery time.

    # If the forward is unwound, this is the forward price at the time that it was unwound.
    # Note that this is the price per unit base currency, not the total unwind price of the entire forward, whose
    # amount can be different than 1.
    unwind_price = models.FloatField(null=True, default=None, blank=True)

    # If the forward is unwound, this is the time at which that occurs.
    unwind_time = models.DateTimeField(null=True, default=None, blank=True)

    # Keep track of the initial forward value that the internal pangea system thought the forward was worth.
    # This helps us compare our data with the data of different brokers.
    initial_pangea_forward_price = models.FloatField(null=True, default=None)

    # ============================
    # FxForwardInstrument
    # ============================

    def get_fxpair(self) -> FxPair:
        return self.fxpair

    def get_amount(self) -> float:
        return self.amount

    def get_forward_price(self) -> float:
        return self.forward_price

    def get_account(self) -> Account:
        return self.account

    def get_delivery_time(self) -> Date:
        return Date.from_datetime(self.delivery_time)

    def get_enter_time(self) -> Date:
        return Date.from_datetime(self.enter_time)

    # ============================
    # Properties
    # ============================

    @property
    def initial_fwd_points(self):
        return self.initial_spot_price - self.forward_price

    @property
    def is_unwound(self) -> bool:
        return self.unwind_time is not None

    @property
    def pnl(self) -> Optional[float]:
        if self.unwind_price:
            return (self.unwind_price - self.forward_price) * self.amount
        return None

    def compute_pnl(self, forward_price: float) -> float:
        """ Compute the PnL given the current forward price. """
        return (forward_price - self.forward_price) * self.amount

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_forwards_for_account(current_time: Date, account: AccountTypes) -> Sequence['FxForwardPosition']:
        account_ = Account.get_account(account)
        if account_ is None:
            raise Account.NotFound(account)
        return FxForwardPosition.objects.filter(Q(unwind_time__isnull=True) | Q(unwind_time__lt=current_time),
                                                account=account_,
                                                enter_time__lte=current_time,
                                                delivery_time__gt=current_time,
                                                )

    @staticmethod
    def get_forwards_for_company(current_time: Date,
                                 company: CompanyTypes,
                                 account_types: Optional[Iterable[Account.AccountType]] = None,
                                 ) -> Iterable['FxForwardPosition']:
        company_ = Company.get_company(company)
        if company_ is None:
            raise Company.NotFound(company)
        filters = {}
        if account_types:
            filters["account__type__in"] = account_types

        return FxForwardPosition.objects.filter(cashflow__account__company=company_,
                                                enter_time__lte=current_time,
                                                delivery_time__gt=current_time,
                                                unwind_time__isnull=True, **filters)

    @staticmethod
    def get_forwards_for_company_by_account(current_time: Date,
                                            company: CompanyTypes
                                            ) -> Dict[Account, List['FxForwardPosition']]:
        company_ = Company.get_company(company)
        if company_ is None:
            raise Company.NotFound(company)
        forwards = FxForwardPosition.get_forwards_for_company(current_time=current_time, company=company_)
        forwards_by_accounts = {}
        for forward in forwards:
            forwards_by_accounts.setdefault(forward.account, []).append(forward)
        return forwards_by_accounts

    @staticmethod
    def get_unwound_forwards(account: Optional[AccountTypes] = None,
                             company: Optional[CompanyTypes] = None,
                             account_types: Optional[Iterable[Account.AccountType]] = None,
                             start_time: Optional[Date] = None,
                             end_time: Optional[Date] = None,
                             include_start_time: bool = True) -> Iterable['FxForwardPosition']:
        """ Get Fx Forwards whose unwind time falls within a window of time. """
        qs = FxForwardPosition._get_objects(account=account, company=company, account_types=account_types)
        filters = {}
        if start_time:
            filters["unwind_time__" + ("gte" if include_start_time else "gt")] = start_time
        if end_time:
            filters["unwind_time__lte"] = end_time
        if not start_time and not end_time:
            filters["unwind_time__gte"] = Date.now()
        return qs.filter(**filters)

    @staticmethod
    def get_delivered_forwards(account: Optional[AccountTypes] = None,
                               company: Optional[CompanyTypes] = None,
                               account_types: Optional[Iterable[Account.AccountType]] = None,
                               start_time: Optional[Date] = None,
                               end_time: Optional[Date] = None,
                               include_start_time: bool = True,
                               only_unclosed: bool = False) -> Iterable['FxForwardPosition']:
        """ Get Fx Forwards whose delivery time falls within a window of time. """
        qs = FxForwardPosition._get_objects(account=account, company=company, account_types=account_types)
        filters = {}
        if start_time:
            filters["delivery_time__" + ("gte" if include_start_time else "gt")] = start_time
        if end_time:
            filters["delivery_time__lte"] = end_time
        if only_unclosed:
            filters["unwind_time__isnull"] = True
        return qs.filter(**filters)

    @staticmethod
    def _get_objects(account: Optional[AccountTypes] = None,
                     company: Optional[CompanyTypes] = None,
                     account_types: Optional[Iterable[Account.AccountType]] = None) -> QuerySet:
        if account_types is None:
            account_types = []

        account_ = None
        if account:
            account_ = Account.get_account(account)

        company_ = None
        if company:
            company_ = Company.get_company(company)

        if not account_ and not company_:
            raise ValueError(f"you must provide either an account or company to get_unwound_forwards")

        filters = {}
        if company_:
            filters["cashflow__account__company"] = company_
        elif account_:
            filters["cashflow__account"] = account_

        if account_types:
            filters["cashflow__account__type__in"] = account_types

        return FxForwardPosition.objects.filter(**filters)

    # ============================
    # Mutators
    # ============================

    @staticmethod
    def add_forward_to_account(
        fxpair: FxPairTypes,
        enter_time: Date,
        delivery_time: Date,
        amount: float,
        forward_price: float,
        spot_price: float,
        account: Optional[Account] = None,
        cashflow: Optional[CashFlow] = None) -> 'FxForwardPosition':

        if not account and not cashflow:
            raise RuntimeError("either account or cashflow must be non-null in add_forwards_to_account")
        if not account:
            account = cashflow.account

        fxpair_ = FxPair.get_pair(fxpair)
        return FxForwardPosition.objects.create(account=account,
                                                cashflow=cashflow,
                                                fxpair=fxpair_,
                                                enter_time=enter_time,
                                                amount=amount,
                                                forward_price=forward_price,
                                                initial_spot_price=spot_price,
                                                delivery_time=delivery_time)


auditlog.register(FxForwardPosition)
