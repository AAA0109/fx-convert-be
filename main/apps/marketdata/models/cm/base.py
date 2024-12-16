from django.db import models
from main.apps.marketdata.models.marketdata import MarketData
from main.apps.currency.models.currency import Currency


class CmAsset(models.Model):
    """
    A commodity asset. E.g. Gold, Silver, Oil
    """
    class Meta:
        verbose_name_plural = "Cm Assets"

    name = models.CharField(max_length=255, null=False, unique=True)  # e.g. 'Gold'
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    units = models.CharField(max_length=50, null=True)  # e.g. 'oz'

    def __str__(self):
        return self.name
    # Note: we may need to associate specific tickers to it, e.g. ICE/BBG


class Cm(MarketData):
    """ Base class for commodity data with date attached (e.g. cm spot) """
    asset = models.ForeignKey(CmAsset, on_delete=models.CASCADE, null=False)

    class Meta:
        abstract = True
