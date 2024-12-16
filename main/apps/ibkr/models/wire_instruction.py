from auditlog.registry import auditlog
from django.db import models

from main.apps.currency.models import Currency


class WireInstruction(models.Model):
    class Meta:
        verbose_name_plural = "Wire Instructions"

    title = models.CharField(max_length=60, null=False)
    bank_name = models.CharField(max_length=60, null=False)
    bank_address = models.TextField(null=True, blank=True)
    beneficiary_name = models.CharField(max_length=60, null=True, blank=True)
    beneficiary_account_number = models.CharField(max_length=60, null=True, blank=True)
    beneficiary_routing_number = models.CharField(max_length=60, null=True, blank=True)
    beneficiary_address = models.TextField(null=True, blank=True)
    wire_reference = models.TextField(null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    swift_bic_code = models.CharField(max_length=60, null=True, blank=True)
    account_info = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title


auditlog.register(WireInstruction)
