from django.db import models

from main.apps.account.models import Company
from main.apps.currency.models import Currency


class SettlementAccount(models.Model):
    class Method(models.TextChoices):
        WIRE = 'W', 'Wire'
        EFT = 'E', 'EFT'
        FXBalance = 'C', 'FX Balance'

    settlement_account_id = models.CharField(max_length=255)
    delivery_method = models.CharField(max_length=1, choices=Method.choices)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    text = models.CharField(max_length=255)
    payment_ident = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=255, null=True)
    bank_account = models.CharField(max_length=255, blank=True)
    preferred = models.BooleanField(default=False)
    selected = models.BooleanField(default=False)
    category = models.CharField(max_length=255, null=True, blank=True)
