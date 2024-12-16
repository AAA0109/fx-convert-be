from django.db import models
from django_extensions.db.models import TimeStampedModel

from main.apps.account.models import Company


class Confirm(TimeStampedModel):
    class Type(models.TextChoices):
        FORWARD = ('forward', 'Forward')
        SPOT = ('spot', 'Spot')

    confirm_type = models.CharField(max_length=7, choices=Type.choices)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    deal_number = models.CharField(max_length=15)
    order_number = models.CharField(max_length=15, null=True, blank=True)
    content = models.JSONField()
