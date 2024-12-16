from typing import Optional

from django.db import models
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company
from main.apps.corpay.models import CorpaySettings
from main.apps.currency.models import FxPair, Currency
from main.apps.util import get_or_none


class TransactionCost(TimeStampedModel):
    currency_category = models.CharField(max_length=10, choices=Currency.CurrencyCategory.choices)
    average_volume_low = models.FloatField(null=True)
    average_volume_high = models.FloatField(null=True)
    notional_low = models.FloatField(null=True)
    notional_high = models.FloatField(null=True)
    cost_in_bps = models.FloatField(null=True)

    @property
    def broker_cost(self) -> float:
        return self.cost_in_bps / 10000.0

    @staticmethod
    @get_or_none
    def get_cost(company: Company, notional_in_usd: float, currency: Currency) -> Optional['TransactionCost']:
        settings = CorpaySettings.get_settings(company=company)
        if not settings:
            raise Exception(f"Corpay settings not found for company {company}")

        return TransactionCost.objects.filter(currency_category = currency.category,
                                           average_volume_low__lte=settings.average_volume,
                                           average_volume_high__gt=settings.average_volume,
                                           notional_low__lt=abs(notional_in_usd),
                                           notional_high__gte=abs(notional_in_usd)).first()


class AumCost(TimeStampedModel):
    currency_category = models.CharField(max_length=10, choices=Currency.CurrencyCategory.choices)
    average_volume_low = models.FloatField(null=True)
    average_volume_high = models.FloatField(null=True)
    annualized_rate = models.FloatField(null=True)
    minimum_rate = models.FloatField(null=True)






