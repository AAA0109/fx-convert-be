from django.db import models
from main.apps.marketdata.models.marketdata import MarketData
from main.apps.currency.models.fxpair import FxPair


class Fx(MarketData):
    pair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)

    class Meta:
        abstract = True
