from django.db import models
from main.apps.marketdata.models.marketdata import MarketData
from main.apps.currency.models.currency import Currency


class EqAsset(models.Model):
    """
    An equity asset. This is either a "Single Name", such as GOOGL, or an index, such as SX5E
    """
    class Meta:
        verbose_name_plural = "eq_assets"

    name = models.CharField(max_length=255, null=False, unique=True)  # e.g. 'SX5E'
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    is_index = models.BooleanField(null=False, default=True)  # true for an equity index, false for a "single name"

    # Note: we may need to associate specific tickers to it, e.g. bloomberg and RIC


class Eq(MarketData):
    """ Base class for equity data with date attached (e.g. eq spot) """
    name = models.ForeignKey(EqAsset, on_delete=models.CASCADE, null=False)
