from typing import Union, Optional

from auditlog.registry import auditlog
from django.db import models

from main.apps.account.models import Account, AccountId

import logging

logger = logging.getLogger(__name__)


class ParachuteData(models.Model):
    """
    Data for accounts that execute the parachute hedging strategy.
    """

    class Meta:
        verbose_name_plural = "parachute_data"

    # The account that is a parachute account.
    account = models.OneToOneField(Account, on_delete=models.CASCADE, null=False, related_name="parachute_data")

    # The value that the account value should not drop below, in fractional terms. The dollar value is computed by
    # multiplying this by the sum of absolute values of all positions.
    lower_limit = models.FloatField(null=False)

    # The probability of breaching the lower limit that, if greater than this, further positions should be taken.
    lower_p = models.FloatField(null=False, default=0.95)

    # The probability that is adjusted to.
    upper_p = models.FloatField(null=False, default=0.99)

    # If true, the first time the account value is in p-danger of breaching the lower limit, a full hedge will be put
    # on. If false, we just hedge back to upper-p, as usual.
    lock_lower_limit = models.BooleanField(null=False, default=False)

    # The fraction of the floating PnL that is used to adjust the lower limit.
    #
    # Zero means standard parachute. Non-zero means that some fraction of the floating PnL is used to adjust the lower
    # limit. This is used to "capture" some of the PnL that the account can make.
    floating_pnl_fraction = models.FloatField(null=False, default=0.0)

    @staticmethod
    def get_for_account(account: Account) -> Optional['ParachuteData']:
        q = ParachuteData.objects.filter(account=account)
        if not q:
            return None
        return q.first()

    @staticmethod
    def create_for_account(account: Account,
                           lower_limit: float,
                           lower_p: float,
                           upper_p: float,
                           floating_pnl_fraction: float = 0.,
                           lock_lower_limit: bool = False) -> 'ParachuteData':
        if floating_pnl_fraction < 0:
            raise ValueError("Floating PnL fraction must be non-negative")
        if floating_pnl_fraction > 1:
            raise ValueError("Floating PnL fraction must be at most 1")
        if lower_p < 0 or lower_p > 1:
            raise ValueError("Lower p must be between 0 and 1")
        if upper_p < 0 or upper_p > 1:
            raise ValueError("Upper p must be between 0 and 1")
        if lower_limit < 0:
            raise ValueError("Lower limit must be non-negative")

        return ParachuteData.objects.create(account=account,
                                            lower_limit=lower_limit,
                                            lower_p=lower_p,
                                            upper_p=upper_p,
                                            floating_pnl_fraction=floating_pnl_fraction,
                                            lock_lower_limit=lock_lower_limit)


auditlog.register(ParachuteData)
