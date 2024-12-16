from django.db import models

from main.apps.account.models import Account


class AutopilotData(models.Model):
    class Meta:
        verbose_name = "Autopilot Data"

    # The account that is a autopilot account
    account = models.OneToOneField(Account, on_delete=models.CASCADE, null=False, related_name="autopilot_data")

    # The upper limit in percentage
    upper_limit = models.FloatField(null=False, blank=True)

    # The lower limit in percentage
    lower_limit = models.FloatField(null=False, blank=True)
