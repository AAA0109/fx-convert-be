from typing import List, Optional
from django.db import models
from django.db.models import Q
from django_extensions.db.models import TimeStampedModel
from hdlib.DateTime.Date import Date


class FutureContract(TimeStampedModel):
    base = models.CharField(max_length=10, null=False, default="")
    con_id = models.IntegerField(null=True)
    currency = models.CharField(max_length=5, null=True)
    description = models.CharField(max_length=150, null=True)
    exchange = models.CharField(max_length=5, null=True)
    exchanges = models.CharField(max_length=50, null=True)
    fut_base = models.CharField(max_length=5, null=False, default="")
    fut_cont_size = models.IntegerField(null=False, default=-1)
    fut_month = models.IntegerField(null=True)
    fut_month_symbol = models.CharField(max_length=5, null=False, default="")
    fut_start_dt = models.DateField(null=True)
    fut_symbol = models.CharField(
        max_length=10, null=False, default="", unique=True)
    fut_val_pt = models.IntegerField(null=False, default=-1)
    fut_year = models.CharField(max_length=5, null=False, default="")
    last_dt = models.DateField(null=True)
    lcode_long = models.CharField(max_length=10, null=False, default="")
    liquid_hours = models.TextField(null=True)
    local_symbol = models.CharField(max_length=10, null=True)
    market_name = models.CharField(max_length=5, null=True)
    min_tick = models.FloatField(null=True)
    multiplier = models.IntegerField(null=True)
    price_magnifier = models.IntegerField(null=True)
    roll_dt = models.DateField(null=True)
    sec_type = models.CharField(max_length=10, null=True)
    symbol = models.CharField(max_length=5, null=True)
    timezone_id = models.CharField(max_length=50, null=True)
    trading_hours = models.TextField(null=True)

    @staticmethod
    def get_active_contract(base: Optional[str], today: Date) -> List['FutureContract']:
        query = Q(base=base) & Q(fut_year__gte=today.year) & Q(fut_year__lt=today.year + 2) & (Q(last_dt__isnull=True) | Q(last_dt__gt=today.strftime("%Y-%m-%d"))) if base else Q(
            fut_year__gte=today.year) & Q(fut_year__lt=today.year + 2) & (Q(last_dt__isnull=True) | Q(last_dt__gt=today.strftime("%Y-%m-%d")))
        return FutureContract.objects.filter(query)


class FutureContractIntra(models.Model):
    future_contract = models.ForeignKey(
        FutureContract, on_delete=models.CASCADE, null=False)

    date = models.DateTimeField()
    base = models.CharField(max_length=10, null=False, default="")
    rate = models.FloatField(null=True)
    rate_bid = models.FloatField(null=True)
    rate_ask = models.FloatField(null=True)

    class Meta:
        unique_together = (("future_contract"),)
