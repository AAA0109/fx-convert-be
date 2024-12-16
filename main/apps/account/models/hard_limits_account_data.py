from typing import Optional

from auditlog.registry import auditlog
from django.db import models

from main.apps.account.models import Account

import logging

logger = logging.getLogger(__name__)


class HardLimitsAccountData(models.Model):
    """
    Data for accounts that execute the parachute hedging strategy.
    """

    class Meta:
        verbose_name_plural = "hard_limits_data"
        unique_together = (("account",),)  # One data per account (at most)

    # The account which is a hard-limits account.
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # The value that the spot rates should not drop below.
    # Fractions should (presumably) be < 1, e.g. 0.95 for a 5% drop.
    lower_limit_fraction = models.FloatField(null=False)

    # If not null, we lock in the rate when it increases by a certain amount in our favor.
    # Fraction should (presumably) be > 1, e.g. 1.05 for a 5% increase.
    upper_limit_fraction = models.FloatField(null=True)

    @staticmethod
    def get_for_account(account: Account) -> Optional['HardLimitsAccountData']:
        q = HardLimitsAccountData.objects.filter(account=account)
        if not q:
            return None
        return q.first()

    @staticmethod
    def create_for_account(account: Account,
                           lower_limit: float,
                           upper_limit: Optional[float] = None) -> 'HardLimitsAccountData':
        return HardLimitsAccountData.objects.create(account=account,
                                                    lower_limit=lower_limit,
                                                    upper_limit=upper_limit)


auditlog.register(HardLimitsAccountData)
