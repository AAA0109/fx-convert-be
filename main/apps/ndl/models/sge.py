from django.db import models
from main.apps.currency.models import Currency

class sge(models.Model):
    date = models.DateField()
    value_type = models.CharField(max_length=50)
    value = models.FloatField(null=True, blank=True)
    currency = models.ForeignKey(Currency, to_field='mnemonic', on_delete=models.CASCADE, related_name="sges")
    country_codes = models.CharField(max_length=250)
