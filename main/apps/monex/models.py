from django.db import models
from django.utils.translation import gettext_lazy as _

from main.apps.account.models import Company, User


# Create your models here.
class MonexCompanySettings(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE)
    entity_id = models.CharField(null=True, blank=True, max_length=100)
    customer_id = models.CharField(null=True, blank=True, max_length=100)
    company_name = models.CharField(null=True, blank=True, max_length=100)


class MonexBankType(models.TextChoices):
        MAIN = "main", _("Main")
        INTER = "inter", _("Inter")
