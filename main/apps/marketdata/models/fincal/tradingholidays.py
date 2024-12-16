from typing import Optional
from django.db import models
from django.utils.translation import gettext as _

from main.apps.util import get_or_none
from main.apps.currency.models.currency import Currency


class TradingHolidaysCodeFincal(models.Model):
    code = models.IntegerField()
    holiday = models.CharField(max_length=255, null=False)

    @staticmethod
    @get_or_none
    def get_tradingholidaycode(code:int) -> Optional['TradingHolidaysCodeFincal']:
        return TradingHolidaysCodeFincal.objects.get(code=code)

    def __str__(self):
        return self.holiday


class TradingHolidaysInfoFincal(models.Model):

    class InfoType(models.TextChoices):
        BANK = "bank", _("Bank")
        SE_TRADING = "se_trading", _("SE Trading")
        SE_SETTLEMENT = "se_settlement", _("SE Settlement")
        FUTURES_TRADING = "futures_trading", _("Futures Trading")
        OTHER = "other", _("Other")

    code = models.CharField(max_length=5, null=False)
    center = models.CharField(max_length=255, null=False)
    country = models.CharField(max_length=255, null=True, blank=True)
    currency = models.CharField(max_length=5, null=True, blank=True)
    info_type = models.CharField(max_length=50, choices=InfoType.choices, null=True, blank=True)
    iso_country = models.CharField(max_length=5, null=True, blank=True)
    define_1 = models.TextField(null=True, blank=True)
    define_2 = models.TextField(null=True, blank=True)

    @staticmethod
    @get_or_none
    def get_tradingholidayinfo(code:str) -> Optional['TradingHolidaysInfoFincal']:
        return TradingHolidaysInfoFincal.objects.get(code=code)

    def __str__(self):
        return self.code


class TradingHolidaysFincal(models.Model):
    date = models.DateField()
    code = models.CharField(max_length=5, null=False)
    status = models.IntegerField(null=True)

    class Meta:
        unique_together = (("date", "code"),)
        indexes = [
            models.Index(fields=['date', 'code']),
        ]
