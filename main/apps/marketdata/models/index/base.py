from django_extensions.db.models import TimeStampedModel
from django.db import models

from main.apps.marketdata.models import MarketData


class IndexAsset(TimeStampedModel):
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=10)

class Index(MarketData):
    index_asset = models.ForeignKey(IndexAsset, on_delete=models.CASCADE, null=False)
    rate_index = models.FloatField(null=True)
    rate_bid_index = models.FloatField(null=True)
    rate_ask_index = models.FloatField(null=True)
