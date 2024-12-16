from django.db import models, IntegrityError
from main.apps.util import get_or_none, ActionStatus

from typing import List, Iterable, Union, Sequence, Optional, Tuple
from .currency import Currency, CurrencyId, CurrencyMnemonic, CurrencyTypes


class StabilityIndex(models.Model):

    class Meta:
        verbose_name_plural = "stability indexes"

    date = models.DateTimeField(null=True)
    parent_index = models.ForeignKey('StabilityIndex', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=255, null=True)
    name = models.CharField(max_length=255, null=True)
    description = models.TextField(null=True)
    value = models.FloatField(null=True, blank=True)
    average_value = models.FloatField(null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name='currency', null=False)

    def __str__(self):
        return f"{self.name}_{self.currency.mnemonic}_{self.date.strftime('%Y')}"
