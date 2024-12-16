from auditlog.registry import auditlog
from django.db import models

from main.apps.account.models.company import Company

import logging

logger = logging.getLogger(__name__)


class Aum(models.Model):
    """
    Asset under managment (AUM) record to support Pangea fees model.
    """

    class Meta:
        verbose_name_plural = "aums"

        # Each company can have a daily aum recorded once per day
        unique_together = (("company", "date"),)

    # Company to which the fee is tied
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='aum_companies', null=False)

    # Daily AUM Amount (always in USD)
    daily_aum = models.FloatField(null=False)

    # Rolling AUM, the average AUM Amount that is used during the AUM fee calculation
    rolling_aum = models.FloatField(null=False)

    # Maximum / desired Number of days used in calculation of rolling window
    rolling_window = models.IntegerField(null=False)

    # Actual number of days used in the rolling aum calc
    actual_window = models.IntegerField(null=False)

    # When this fee was recorded in our system
    recorded = models.DateTimeField(auto_now_add=True, blank=False)

    # The date this fee is associated with
    date = models.DateField(auto_now_add=False, blank=False)

auditlog.register(Aum)
