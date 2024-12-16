from typing import Tuple, Optional, Iterable

from auditlog.registry import auditlog
from django.db import models

from main.apps.broker.models import Broker, BrokerTypes
from main.apps.currency.models import Currency, CurrencyTypes
from main.apps.util import ActionStatus, get_or_none


class TieredRate(models.Model):
    class Meta:
        abstract = True

    # date identifier for when the data was parsed,
    # this is to prevent duplicate entries from inserted if the scraper run multiple times in the same date
    date = models.DateField(null=True)

    # The broker for which this is data.
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, null=False)

    # The currency.
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, blank=False)

    # The bottom tier for which this rate is relevant. This cannot be null, since the min possible amount is zero.
    tier_from = models.FloatField(null=True, blank=True)
    # The bottom tier for which this rate is relevant. This can be null, which signifies there is no tier above this.
    tier_to = models.FloatField(null=True, blank=True)

    # The rate at which this tier is charged or charges interest
    rate = models.FloatField(null=False, blank=False)

    # broker spread
    spread = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CurrencyMargin(TieredRate):
    @staticmethod
    @get_or_none
    def get_rates(currency: CurrencyTypes, broker: BrokerTypes) -> Iterable['CurrencyMargin']:
        # TODO: add filter for the date
        return CurrencyMargin.objects.filter(currency=currency, broker=broker).order_by("tier_from")

    @staticmethod
    def set_rate(currency: CurrencyTypes,
                 broker: BrokerTypes,
                 rate: float) -> Tuple[ActionStatus, Optional['CurrencyMargin']]:
        currency_ = Currency.get_currency(currency)
        if not currency_:
            return ActionStatus.log_and_error(f"Currency {currency} does not exist."), None
        broker_ = Broker.get_broker(broker)
        if not broker_:
            return ActionStatus.log_and_error(f"Could not find broker {broker}."), None
        objs = CurrencyMargin.objects.filter(currency=currency_, broker=broker_)
        if objs:
            margin = objs.first()
            margin.rate = rate
            margin.save()
        else:
            margin, created = CurrencyMargin.objects.get_or_create(currency=currency_, broker=broker_, rate=rate)
        return ActionStatus.log_and_success(f"Set currency margin rate for {currency_}, "
                                            f"broker {broker_} to be {rate}."), margin

auditlog.register(CurrencyMargin)
