from typing import Dict

import numpy as np
from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.currency.models.fxpair import Currency
from main.apps.hedge.models import CompanyEvent

import logging

logger = logging.getLogger(__name__)


class CompanyCashHolding(models.Model):
    """
    Represents current actual cash currently holdings of a company.
    """

    class Meta:
        verbose_name_plural = "Company FX Positions"
        unique_together = (("snapshot_event", "broker_account", "currency"),)

    # The snapshot even that caused this positions snapshot.
    snapshot_event = models.ForeignKey(CompanyEvent, on_delete=models.CASCADE, null=False)

    # The broker with which this position is held. Broker account being null means these are positions for a
    # DEMO account.
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE,
                                       related_name="fxbroker_account_cch", null=True)

    # The FX pair in which we have a position (these are always stored in the MARKET traded convention)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='company_currency_cch', null=False)

    # Amount of this fx pair which defines the position (also = total price in the base currency)
    amount = models.FloatField(null=False, default=0.)

    @staticmethod
    def create_cash_holdings(event: CompanyEvent,
                             broker_account: BrokerAccount,
                             cash_holdings: Dict[Currency, float]):
        holdings = []
        for currency, amount in cash_holdings.items():
            # The data coming from IBKR has a null currency for one entry.
            if amount != 0.0 and currency is not None:
                holdings.append(
                    CompanyCashHolding(snapshot_event=event,
                                       broker_account=broker_account,
                                       currency=currency,
                                       amount=amount))
        if 0 < len(holdings):
            logger.debug(f"Ready to create {len(holdings)} cash holdings.")
            CompanyCashHolding.objects.bulk_create(holdings)
            logger.debug(f"Bulk created {len(holdings)} cash holdings.")


auditlog.register(CompanyCashHolding)
