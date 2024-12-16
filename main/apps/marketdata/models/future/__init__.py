from django.db import models
from main.apps.ibkr.models.future_contract import FutureContract
from main.apps.marketdata.models.marketdata import MarketData


class FutureMarketData(MarketData):
    future_contract = models.ForeignKey(FutureContract, on_delete=models.CASCADE, null=False)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        abstract = True
