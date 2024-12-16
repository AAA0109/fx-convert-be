from django.db import models
from main.apps.marketdata.models.ir import Ir
from hdlib.DateTime.DayCounter import DayCounter


class Issuer(models.Model):
    """
    Issuer of the bond. e.g. "United Mexican States".
    """
    name = models.CharField(max_length=255, null=False, unique=True)


class GovBond(Ir):
    """
    Represents the price/yield of a government bond by a sovereign issuer (e.g. Canada).
    Note: multiple countries can issue bonds in the same currency, e.g. EUR
    """
    issuer = models.ForeignKey(Issuer, on_delete=models.CASCADE, null=False)
    tenor = models.CharField(max_length=10, null=False)
    maturity = models.DateField(null=False)
    maturity_days = models.IntegerField(null=True)
    ytm = models.FloatField(null=False)  # Yield-to-maturity
    price = models.FloatField(null=False)
    coupon = models.FloatField(null=False)

    class Meta:
        unique_together = (("data_cut", "tenor", "issuer"),)

    def ttm(self, day_counter: DayCounter) -> float:
        """ Calculates the time to maturity for this discount factor """
        return day_counter.year_fraction_from_days(days=self.maturity_days)

    # ============================
    # Accessors
    # ============================
