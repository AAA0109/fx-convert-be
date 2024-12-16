from auditlog.registry import auditlog
from django.db import models

from main.apps.broker.models import Broker
from main.apps.currency.models import Currency


class BenchmarkRate(models.Model):
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, null=False)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, blank=False)
    description = models.CharField(max_length=255, null=False, blank=False)
    rate = models.FloatField(null=False, blank=False)
    effective_date = models.DateField(null=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


auditlog.register(BenchmarkRate)
