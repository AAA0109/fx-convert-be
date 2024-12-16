from django.db import models

from main.apps.account.models import Company


# Create your models here.
class NiumSettings(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE)
    customer_hash_id = models.CharField(max_length=60, null=True, blank=True)
