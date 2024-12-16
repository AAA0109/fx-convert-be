from typing import Optional, Iterable

from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import Account
from main.apps.hedge.models.fxforwardposition import FxForwardPosition

import logging

logger = logging.getLogger(__name__)


class ForwardSettlement(models.Model):
    """
    Represents forward being settled, or unwound / drawn-down (completely or partially).
    """

    class Meta:
        verbose_name_plural = "Company FX Positions"
        unique_together = (("parent_forward", "settlement_time"),)

    # The cashflow that the rolled-off cashflow is associated with. Note that since a DB cashflow is really a cashflow
    # generator, but the CashflowRolloff tracks when actual cashflows roll off,
    parent_forward = models.ForeignKey(FxForwardPosition, on_delete=models.CASCADE, null=False)

    # The time at which the roll-off occurred.
    settlement_time = models.DateTimeField(null=False)

    # Amount of the forward that was unwound. For an american forward, you can draw down the forward in parts.
    amount_unwound = models.FloatField(null=False, default=0.)

    # The amount that was remaining after the draw-down.
    amount_remaining = models.FloatField(null=False, default=0.)

    # The Fx rate at which the forward unwound.
    unwind_fx_rate = models.FloatField(null=False, default=0.)

    @property
    def pnl(self):
        return self.parent_forward.pnl

    @staticmethod
    def register_settlement(parent_forward: FxForwardPosition,
                            settlement_time: Date,
                            amount_unwound: float,
                            amount_remaining: float,
                            unwind_fx_rate: float):
        """ Register the partial or complete settlement (or draw-down) of a forward contract. """
        return ForwardSettlement.objects.create(parent_forward=parent_forward, settlement_time=settlement_time,
                                                amount_unwound=amount_unwound, amount_remaining=amount_remaining,
                                                unwind_fx_rate=unwind_fx_rate)

    @staticmethod
    def get_forward_settlements(account: Account,
                                start_time: Optional[Date],
                                end_time: Optional[Date]) -> Iterable['ForwardSettlement']:
        filters = {"parent_forward__cashflow__account": account}
        if start_time:
            filters["settlement_time__gt"] = start_time
        if end_time:
            filters["settlement_time__lte"] = end_time
        return ForwardSettlement.objects.filter(**filters)


auditlog.register(ForwardSettlement)
