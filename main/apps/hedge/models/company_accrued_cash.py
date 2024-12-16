import numpy as np
from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.currency.models.fxpair import FxPair, Currency
from main.apps.hedge.models import CompanyEvent
from main.apps.util import get_or_none

from typing import Sequence, Optional, Tuple, Dict, List

import logging

logger = logging.getLogger(__name__)


class CompanyAccruedCash(models.Model):
    """
    Represents cash currently accrued by a company.
    """

    class Meta:
        verbose_name_plural = "Company FX Positions"
        unique_together = (("snapshot_event", "broker_account", "currency"),)

    # The snapshot even that caused this positions snapshot.
    snapshot_event = models.ForeignKey(CompanyEvent, on_delete=models.CASCADE, null=False)

    # The broker with which this position is held. Broker account being null means these are positions for a
    # DEMO account.
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE,
                                       related_name="fxbroker_account_cac", null=True)

    # The FX pair in which we have a position (these are always stored in the MARKET traded convention)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='company_currency_cac', null=False)

    # Amount of this fx pair which defines the position (also = total price in the base currency)
    amount = models.FloatField(null=False, default=0.)

    @staticmethod
    def create_accrued_cash_record(event: CompanyEvent,
                                   broker_account: BrokerAccount,
                                   cash_holdings: Dict[Currency, float]):
        record = []
        for currency, amount in cash_holdings.items():
            # The data coming from IBKR has a null currency for one entry.
            if amount != 0.0 and currency is not None:
                record.append(
                    CompanyAccruedCash(snapshot_event=event,
                                       broker_account=broker_account,
                                       currency=currency,
                                       amount=amount))
        if 0 < len(record):
            logger.debug(f"Ready to create {len(record)} accrued cash records.")
            CompanyAccruedCash.objects.bulk_create(record)
            logger.debug(f"Bulk created {len(record)} accrued cash records.")


auditlog.register(CompanyAccruedCash)
