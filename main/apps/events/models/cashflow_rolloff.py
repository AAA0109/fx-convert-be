from typing import Optional

from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CashFlow, Account

import logging

logger = logging.getLogger(__name__)


class CashflowRolloff(models.Model):
    """
    Represents cash flow "rolling off" i.e. being paid or received by an account.
    """

    class Meta:
        # Note that we cannot have a uniqueness constraint on the (parent_cashflow, rolloff_time) pair, since
        # we can have cashflows "stack up" over the weekend (like if we have cashflows that pay on the 1st and 2nd,
        # but the 1st is a Saturday, they will both roll so that the pay date is a monday.

        verbose_name_plural = "Cashflow Rolloffs"


    # The cashflow that the rolled-off cashflow is associated with. Note that since a DB cashflow is really a cashflow
    # generator, but the CashflowRolloff tracks when actual cashflows roll off,
    parent_cashflow = models.ForeignKey(CashFlow, on_delete=models.CASCADE, null=False)

    # The time at which the roll-off occurred.
    rolloff_time = models.DateTimeField(null=False)

    # Amount of the cashflow, in the foreign currency.
    amount = models.FloatField(null=False, default=0.)

    # The final fx spot rate of the cashflow at the time it rolled off, the per-unit price of the cashflow at roll-off
    # time.
    final_rate = models.FloatField(null=False, default=0.)

    @property
    def final_value(self):
        return self.final_rate * self.amount

    @staticmethod
    def register_rolloff(parent_cashflow: CashFlow, rolloff_time: Date, amount: float, final_rate: float):
        return CashflowRolloff.objects.create(parent_cashflow=parent_cashflow, rolloff_time=rolloff_time,
                                              amount=amount, final_rate=final_rate)

    @staticmethod
    def get_rolloffs(account: Account, start_time: Optional[Date] = None, end_time: Optional[Date] = None):
        filters = {"parent_cashflow__account": account}
        if start_time:
            filters["rolloff_time__gt"] = start_time
        if end_time:
            filters["rolloff_time__lte"] = end_time
        return CashflowRolloff.objects.filter(**filters)


auditlog.register(CashflowRolloff)
