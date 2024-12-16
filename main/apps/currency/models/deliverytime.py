from typing import Optional
from django.db import models
from django_extensions.db.models import TimeStampedModel
from main.apps.util import get_or_none
from main.apps.corpay.api.serializers.choices import DELIVERY_METHODS
from main.apps.currency.models.currency import Currency


class DeliveryTime(TimeStampedModel):

    class Meta:
        verbose_name = "Bank Country Session"
        verbose_name_plural = "Bank Country Sessions"


    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, verbose_name="Default Currency")

    country = models.CharField(max_length=255, null=False, verbose_name="Bank Country")

    # Currency delivery method. e.g. wire, iach
    delivery_method = models.CharField(max_length=50, choices=DELIVERY_METHODS, null=True)

    # Currency delivery sla in bussiness days
    delivery_sla = models.IntegerField(null=True)

    # Currency delivery deadline
    deadline = models.TimeField(null=True)

    # Bank session open time in UTC.
    banking_open_utc = models.TimeField(null=True, help_text="Bank session open time in UTC")

    # Bank session close time in UTC.
    banking_close_utc = models.TimeField(null=True, help_text="Bank session open time in UTC")

    @staticmethod
    @get_or_none
    def get_deliverytime_by_currency(currency: Currency) -> Optional['DeliveryTime']:
        return DeliveryTime.objects.get(currency=currency)

    def __str__(self) -> str:
        return f"Bank Session ({self.pk})"
