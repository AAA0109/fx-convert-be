from django.db import models
from main.apps.marketdata.models.marketdata import MarketData
from main.apps.currency.models.currency import Currency


class Ir(MarketData):
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)

    class Meta:
        abstract = True
