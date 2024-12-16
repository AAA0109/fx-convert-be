import numpy as np
from auditlog.registry import auditlog
from django.db import models

from hdlib.Core.FxPairInterface import FxPairInterface

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company
from main.apps.account.models.account import Account, AccountTypes
from main.apps.currency.models.fxpair import FxPair, FxPairTypes, Currency
from main.apps.hedge.models.company_event import CompanyEvent
from main.apps.hedge.support.account_hedge_interfaces import AccountHedgeResultInterface
from main.apps.hedge.support.fxposition_interface import FxPositionInterface
from main.apps.util import get_or_none

from typing import List, Sequence, Optional, Tuple, Dict, Iterable, Set

import logging

logger = logging.getLogger(__name__)

# ==================
# Type definitions
# ==================

HedgeId = int  # represents the primary key for a FxHedgeAction


class FxPosition(models.Model, FxPositionInterface):
    """
    Represents the FX hedge position associated with a Pangea account (NOT a broker account).

    NOTE: these are the FX positions corresponding to "shadow" accounts that only exist as Pangea abstractions.
    These accounts are unknown to the broker(s), they are ways for us to isolate sets of cashflows into groups
    (that we call accounts) which have their own hedge settings, and can be optimized independently. Hence, we
    maintain a record of the FX positions at the account level, but when we submit orders to a broker(s) the
    FX positions are always aggregated up to the company level. The account with our broker(s) only functions
    at a company level, and does not understand our Pangea Accounts. The official record of what are true positions
    at the company level is determined by the broker(s). Any discrepancy between our internal Pangea account
    positions (when aggregated to the company level) and what the broker believes the positions at the company to be,
    must be reconciled to maintain agreement with the broker.
    """

    class Meta:
        verbose_name_plural = "fxpositions"
        unique_together = (("company_event", "account", "fxpair"),)

    # The Pangea account (not the broker account)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='fxaccount', null=False)

    # The FX pair in which we have a position (these are always stored in the MARKET traded convention)
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, related_name='fxpair', null=False)

    # Amount of this fx pair which defines the position (also = total price in the base currency)
    amount = models.FloatField(null=False, default=0.)

    # Company event linking the fx positions together.
    company_event = models.ForeignKey(CompanyEvent, on_delete=models.CASCADE, null=False)

    # Total price for the entire position (always positive), in the quote currency: sum_i (|Q_i| * Spot(t_i))
    # Note that trades in the opposite direction of the current amount will reduce the total price
    total_price = models.FloatField(null=False, default=0.)

    # ============================
    # FxPositionInterface
    # ============================

    def get_fxpair(self) -> FxPairInterface:
        return self.fxpair

    def get_amount(self) -> float:
        return self.amount

    def get_total_price(self) -> float:
        return self.total_price

    def get_account(self) -> Account:
        return self.account

    # ============================
    # Properties
    # ============================

    @property
    def average_price(self) -> Tuple[float, Currency]:
        """ Receive the average price (always positive) paid or received on the position, in the quote currency """
        value = self.total_price / self.amount if self.amount != 0 else 0
        return np.abs(value), self.fxpair.quote_currency

    @property
    def is_long(self) -> bool:
        """ Is this a long position (else short) """
        return self.amount >= 0

    @property
    def is_empty(self) -> bool:
        return self.amount == 0

    def unrealized_pnl(self, current_rate: float) -> Tuple[float, Currency]:
        """
        Retrieve the unrealized PnL in the quote currency
        :param current_rate: float, the current FX rate corresponding to this position
        :return: [PnL, Currency], the unrealized pnl of this position at the current rate
        """
        if self.amount == 0:
            return 0.0, self.fxpair.quote_currency
        return self.amount * current_rate - np.sign(self.amount) * self.total_price, self.fxpair.quote_currency

    # ============================
    # Creation
    # ============================

    @staticmethod
    def create_positions(account_hedge_results: Iterable[AccountHedgeResultInterface],
                         company_event: CompanyEvent) -> Iterable['FxPosition']:
        """
        The main method for creating an FxPosition object from a hedge results object and the company event that the
        positions are associated with.
        """
        fx_positions = []
        for result in account_hedge_results:
            request = result.get_request()
            position = FxPosition(account=request.get_account(),
                                  fxpair=request.get_fx_pair(),
                                  amount=result.get_filled_amount(),
                                  company_event=company_event,
                                  total_price=np.abs(result.get_total_price())  # Total price is always positive.
                                  )
            fx_positions.append(position)

        company_event.has_account_fx_snapshot = True
        company_event.save()
        if 0 < len(fx_positions):
            return FxPosition.objects.bulk_create(fx_positions)
        return []

    @staticmethod
    def raw_create_positions(account: AccountTypes,
                             company_event: CompanyEvent,
                             positions: Dict[FxPair, Tuple[float, float]]  # Amount, TotalPrice
                             ) -> Iterable['FxPosition']:
        """
        Generally, create_positions should be used to create an FxPosition. But for some applications, like for unit
        testing, it is useful to create a positions object from its individual fields.
        """
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)

        fx_positions = []
        for fxpair, (amount, total_price) in positions.items():
            fx_positions.append(FxPosition(account=account_, fxpair=fxpair,
                                           amount=amount, total_price=total_price,
                                           company_event=company_event))

        company_event.has_account_fx_snapshot = True
        company_event.save()
        if 0 < len(fx_positions):
            return FxPosition.objects.bulk_create(fx_positions)
        return []

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_position_objs(company: Optional[CompanyTypes] = None,
                          account: Optional[AccountTypes] = None,
                          account_types: Optional[Sequence[Account.AccountType]] = None,
                          time: Optional[Date] = None,
                          inclusive: bool = True
                          ) -> Tuple[Sequence['FxPosition'], CompanyEvent]:
        """
        Get the Fx positions for a company, aggregated across all accounts.

        :param company: CompanyTypes, identifier for a company.
        :param account: AccountTypes, a specific account to get positions for.
        :param account_types: Iterable, What types of account we want the positions for.
        :param time: Date, the time as of which we want the positions.
        :param inclusive, bool If true, include positions from exactly this time.
        :return: Dict, the positions in the database, in market traded convention.
        """

        account_ = None  # Initialize account_ to None.
        if not account and not company:
            raise ValueError(f"either company or account must be provided")
        if not company:
            account_ = Account.get_account(account)
            if not account_:
                raise Account.NotFound(account)
            company_ = account_.company
        else:
            company_ = Company.get_company(company)

        # Explicitly check for has_account_fx_positions = True, even though (during real operation) this should only
        # occur when has_company_fx_positions is also True.
        event = CompanyEvent.get_event_of_most_recent_positions(company=company_, time=time, inclusive=inclusive,
                                                                check_account_positions=True)

        if not event:
            return [], event

        filters = {"company_event": event}
        if account_types is not None:
            filters["account__type__in"] = account_types
        # If an account was specified, only fetch positions associated with that account.
        if account_:
            filters["account"] = account_

        return FxPosition.objects.filter(**filters), event

    @staticmethod
    def get_positions_per_event_per_account(company: CompanyTypes,
                                            start_date: Optional[Date] = None,
                                            end_date: Optional[Date] = None
                                            ) -> Dict[CompanyEvent, Dict[Account, List['FxPosition']]]:
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)
        filters = {"account__company": company_}
        if start_date:
            filters["company_event__time__gte"] = start_date
        if end_date:
            filters["company_event__time__lte"] = end_date
        positions = FxPosition.objects.filter(**filters)
        output = {}
        for fxposition in positions:
            output.setdefault(fxposition.company_event, {}).setdefault(fxposition.account, []).append(fxposition)
        return output

    @staticmethod
    @get_or_none
    def get_positions_for_accounts(time: Date, accounts: Iterable[Account]
                                   ) -> Tuple[Iterable['FxPosition'], Set[CompanyEvent]]:
        # Get most recent events for all accounts
        events = set([CompanyEvent.get_event_of_most_recent_positions(company=account.company, time=time)
                      for account in accounts])

        objs = FxPosition.objects.filter(company_event__in=events)
        if not objs:
            return [], set({})
        return objs, events

    @staticmethod
    def get_positions_map_for_accounts(time: Date,
                                       accounts: Iterable[Account]) -> Optional[Dict[Account, Dict[FxPair, float]]]:
        objs, _ = FxPosition.get_positions_for_accounts(time=time, accounts=accounts)
        if objs is None:
            return None
        output = {}
        for obj in objs:
            output.setdefault(obj.account, {})[obj.fxpair] = obj.amount
        return output

    @staticmethod
    def get_positions_per_account_per_fxpair(
        time: Date,
        company: Company,
        account_type: Optional[Account.AccountType] = None,
        inclusive: bool = True) -> Tuple[Dict[FxPair, Dict[Account, FxPositionInterface]], CompanyEvent]:

        objs, event = FxPosition.get_position_objs(time=time, company=company, inclusive=inclusive)
        output = {}
        for obj in objs:
            if account_type is not None and obj.account.type != account_type:
                continue  # Potentially filter by account type.
            output.setdefault(obj.fxpair, {})[obj.account] = obj
        return output, event

    @staticmethod
    @get_or_none
    def get_single_position_obj_for_account(account: AccountTypes,
                                            fx_pair: FxPairTypes) -> Optional['FxPosition']:
        """
        Get the amount of a single FX spot held by an account.
        """
        fx_pair_ = FxPair.get_pair(fx_pair)
        if fx_pair_ is None:
            return None

        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)
        CompanyEvent.get_event_of_most_recent_positions(company=account.company)
        qs = FxPosition.objects.filter(account=account, fxpair=fx_pair_) \
            .order_by("-company_event__time")
        return qs.first() if qs else None

    @staticmethod
    def get_positions_by_event_and_account(account: Optional[AccountTypes] = None,
                                           company: Optional[CompanyTypes] = None,
                                           start_time: Optional[Date] = None,
                                           end_time: Optional[Date] = None,
                                           ) -> Dict[CompanyEvent, Dict[Account, List['FxPosition']]]:
        if company is None and account is None:
            raise ValueError(f"one of account or company must not be None")

        filters = {}
        if start_time is not None:
            filters["company_event__time__gte"] = start_time
        if end_time is not None:
            filters["company_event__time__lte"] = end_time
        if account is not None:
            account_ = Account.get_account(account)
            if not account_:
                raise Account.NotFound(account)
            filters["account"] = account_
        if company:
            company_ = Company.get_company(company)
            if not company_:
                raise ValueError(f"could not find company {company}")
            filters["company_event__company"] = company_

        objs = FxPosition.objects.filter(**filters)
        positions: Dict[CompanyEvent, Dict[Account, List[FxPosition]]] = {}
        for obj in objs:
            positions.setdefault(obj.company_event, {}).setdefault(obj.account, []).append(obj)
        return positions


auditlog.register(FxPosition)
