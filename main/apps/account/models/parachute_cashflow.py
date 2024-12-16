import logging
from abc import abstractmethod
from typing import Optional, Sequence

import numpy as np
from auditlog.registry import auditlog
from django.db import models
from django.db.models import Q
from django_extensions.db.models import TimeStampedModel

from hdlib.DateTime.Date import Date

from main.apps.account.models import CashFlow
from main.apps.account.models.account import Account
from main.apps.currency.models.currency import Currency

logger = logging.getLogger(__name__)


class ParachuteCashFlow(TimeStampedModel):
    """
    Model for the literal cashflows that are in a Parachute account.

    Note(Nate): This is a prototype for what I want the CashFlows table to look like when we refactor to separate
    CashFlows from CashFlowGenerators.
    """

    # If a cashflow generator generated this cashflow, this links back to that generator.
    # NOTE: For now the CashFlow model is a generator.
    cashflow_generator = models.ForeignKey(CashFlow, null=True, on_delete=models.SET_NULL)

    # ========================================================================================
    #  Cashflow definition
    # ========================================================================================

    # The pay date of the cashflow, when its received/paid
    pay_date = models.DateTimeField()

    # Currency of the cashflow
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='%(class)s_currency', null=False)

    # Amount of the cashflow in its currency
    amount = models.FloatField(null=False)

    # The account that the cashflow belongs to.
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # ========================================================================================
    #  Statistics
    # ========================================================================================

    # The date/time the cashflow "rolled on" (was created by a generator) or was otherwise created.
    # Note: We keep this separately from the TimeStampedModel fields since those will not be accurate during a
    # backtest, or in other cases where we want to set the creation date to a specific time other than now.
    generation_time = models.DateTimeField()

    # The time at which a cashflow either rolled off, or was "deleted." If this is null, then the cashflow is active.
    deactivation_date = models.DateTimeField(null=True, default=None)

    # Indicates whether a cashflow deactivated due to rolling off (true) as opposed to by being "deleted" (false).
    # Will be null if the cashflow is active.
    deactivated_by_rolloff = models.BooleanField(null=True, default=None)

    # The NPV of the cashflow (per-unit) when it rolled on or was otherwise created.
    # NOTE(Nate): Not sure if this should be nullable or not.
    initial_npv = models.FloatField(null=True)

    # The spot of the [currency][domestic] FX at the time the cashflow rolled on or was otherwise created.
    initial_spot = models.FloatField(null=False)

    # Final NPV of the cashflow - not that *if* the cashflow deactivates by rolloff, this will be equal to final spot,
    # otherwise, it may be different.
    final_npv = models.FloatField(null=True, default=None)
    # The final spot value of the cashflow.
    final_spot = models.FloatField(null=True, default=None)

    # ========================================================================================
    #  Member functions
    # ========================================================================================

    def deactivate_cashflow(self, time: Date, final_npv: float, final_spot: float):
        self._close(time=time, final_unit_npv=final_npv, final_spot=final_spot, did_rolloff=False)

    def close_by_rolloff(self, time: Date, final_spot: float):
        if np.isnan(final_spot):
            logger.warning(f"Cannot close cashflow, final spot is NaN.")
        self._close(time=time, final_unit_npv=final_spot, final_spot=final_spot, did_rolloff=True)

    def _close(self, time: Date, final_unit_npv: float, final_spot: float, did_rolloff: bool):
        if self.deactivation_date is not None:
            # Already deactivated.
            return

        self.deactivation_date = time
        self.deactivated_by_rolloff = did_rolloff
        self.final_npv = final_unit_npv * self.amount
        self.final_spot = final_spot
        self.save()

    @property
    def realized_pnl(self) -> Optional[float]:
        """ If the cashflow is closed, return its PnL. """
        return self.final_npv - self.initial_npv if self.final_npv else None

    # ========================================================================================
    #  Static methods
    # ========================================================================================

    @staticmethod
    def create_cashflow(account: Account,
                        pay_date: Date,
                        currency: Currency,
                        amount: float,
                        generation_time: Date,
                        initial_npv: float,
                        initial_spot: float,
                        generator: Optional[CashFlow] = None) -> 'ParachuteCashFlow':
        """
        Create a parachute cashflow, representing a single cashflow at a single time.

        :param account: The account the cashflow belongs to
        :param pay_date: The time at which cash is exchanged
        :param currency: The currency of the payment
        :param amount: The amount of currency being recieved (positive) or paid (negative)
        :param generation_time: The time at which this cashflow was "generated." The initial NPV and spot are valid as
            of this time
        :param initial_npv: The NPV of one unit of the FX pair [currency][account-currency] at the generation time
        :param initial_spot: The spot price of the FX pair [currency][account-currency] at the generation time
        :param generator: If the cashflow was created by a cashflow generator, this is the generator that create it.
        """
        return ParachuteCashFlow.objects.create(account=account,
                                                cashflow_generator=generator,
                                                pay_date=pay_date,
                                                currency=currency,
                                                amount=amount,
                                                generation_time=generation_time,
                                                initial_npv=initial_npv,
                                                initial_spot=initial_spot)

    @staticmethod
    def get_account_cashflows(ref_date: Date,
                              account: Account,
                              include_rolled_off: bool = False,
                              allow_deactivated: bool = False,
                              start_pay_date: Optional[Date] = None,
                              end_pay_date: Optional[Date] = None) -> Sequence['ParachuteCashFlow']:
        """
        Get all cashflows for an account.
        TODO: Unit test.
        """
        q_statement = Q(generation_time__lte=ref_date) & Q(account=account)

        if include_rolled_off:
            # Only filter out things that were deactivated *not* by rolloff as of the ref_date.
            q_statement &= ~(Q(deactivated_by_rolloff=False) & Q(deactivation_date__lte=ref_date))
        else:
            q_statement &= Q(deactivation_date__isnull=True) | Q(deactivation_date__gt=ref_date)

        # If we don't want deactivated cashflows
        if not allow_deactivated:
            q_statement &= (Q(deactivated_by_rolloff__isnull=True) | Q(deactivated_by_rolloff=True) |
                            Q(deactivation_date__gt=ref_date))
        if start_pay_date:
            q_statement &= Q(pay_date__gte=start_pay_date)
        if end_pay_date:
            q_statement &= Q(pay_date__lte=end_pay_date)

        return ParachuteCashFlow.objects.filter(q_statement)


auditlog.register(ParachuteCashFlow)
