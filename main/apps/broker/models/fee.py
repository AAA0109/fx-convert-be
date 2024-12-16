from typing import List, Optional

from django.db import models
from auditlog.registry import auditlog
from main.apps.account.models.company import Company

from main.apps.broker.models import Broker
from main.apps.currency.models import Currency
from main.apps.marketdata.models.ref.instrument import InstrumentTypes


class CurrencyFee(models.Model):
    class Meta:
        verbose_name = "Broker Fees"
        ordering = ['buy_currency__mnemonic']
        unique_together = ('broker', 'buy_currency', 'sell_currency', 'instrument_type')

    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='currency_fees')
    buy_currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    sell_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True, related_name='broker_fee_sell_currency')
    instrument_type = models.CharField(max_length=50, choices=InstrumentTypes.choices, null=True)

    # legacy
    cost = models.FloatField(null=True, blank=False)

    # fees
    broker_cost = models.FloatField(default=0.0, null=False, blank=False)
    broker_fee = models.FloatField(default=0.0, null=False, blank=False)
    pangea_fee = models.FloatField(default=0.0, null=False, blank=False)
    rev_share = models.FloatField(default=0.4, null=False, blank=False)
    wire_fee = models.FloatField(default=0.0, null=False, blank=False)

    @staticmethod
    def get_cost(currency: str, broker: Broker):
        return CurrencyFee.objects.get(broker=broker, buy_currency__mnemonic=currency).cost

    @staticmethod
    def get_max(currencies: List[str], broker: Broker):
        return CurrencyFee.objects.filter(
            buy_currency__mnemonic__in=currencies,
            broker=broker
        ).aggregate(cost=models.Max('cost', default=0))['cost']

    def get_fees(currencies: List[str], broker: Broker, is_spot:Optional[bool] = None):
        if is_spot is None:
            return CurrencyFee.objects.filter(
                buy_currency__mnemonic__in=currencies,
                broker=broker
            )
        if is_spot:
            return CurrencyFee.objects.filter(
                    buy_currency__mnemonic__in=currencies,
                    broker=broker,
                    instrument_type=InstrumentTypes.SPOT
                )
        return CurrencyFee.objects.filter(
                    buy_currency__mnemonic__in=currencies,
                    broker=broker
                ).exclude(instrument_type=InstrumentTypes.SPOT)

    def __repr__(self):
        return f"{self.buy_currency}: {self.cost}"


class BrokerFeeCompany(models.Model):
    class Meta:
        unique_together = ('broker', 'buy_currency', 'sell_currency', 'instrument_type', 'company')

    company = models.ForeignKey(Company, null=False, on_delete=models.CASCADE)
    broker = models.ForeignKey(Broker, null=False, on_delete=models.CASCADE)
    buy_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='broker_fee_company_buy_currency')
    sell_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='broker_fee_company_sell_currency')
    instrument_type = models.CharField(max_length=50, choices=InstrumentTypes.choices, null=True)

    # fees
    broker_cost = models.FloatField(default=0.0, null=False, blank=False)
    broker_fee = models.FloatField(default=0.0, null=False, blank=False)
    pangea_fee = models.FloatField(default=0.0, null=False, blank=False)
    rev_share = models.FloatField(default=0.0, null=False, blank=False)
    wire_fee = models.FloatField(default=0.0, null=False, blank=False)

    def __repr__(self):
        return f"{self.buy_currency}: {self.cost}"


auditlog.register(CurrencyFee)
