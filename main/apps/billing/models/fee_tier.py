from auditlog.registry import auditlog
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from main.apps.account.models.company import Company, CompanyTypes

from typing import Sequence, Optional, Tuple, Union, Iterable

import logging

logger = logging.getLogger(__name__)


class FeeTier(models.Model):
    """
    Tiers for Pangea fees model. Each fee is invoiced to a customer, for a particular reason
    (e.g. a daily AUM maintenance fee, a new cashflow fee). The "volume" of buisness the customer does with us,
    as measured by some backward looking average over their AUM (assets under management) for example, determines
    which tier this company lies in when it comes to billing
    """

    class Meta:
        verbose_name_plural = "feetiers"
        unique_together = (("company", "tier_from"),)  # Accounts per company must be uniquely named

    # When this fee schedule entry was created in the system
    created = models.DateTimeField(auto_now_add=True, blank=False)

    # When this fee schedule entry was updated in the system
    updated = models.DateTimeField(auto_now_add=True, blank=False)

    # The bottom of a tier (stops at the next bottom). This cannot be null, since the min possible amount is zero.
    # This corresponds to a measure of the AUM of a company
    tier_from = models.FloatField(null=False, validators=[MinValueValidator(0.0), ])

    # Company to which the fee schedule is tied
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='schedule_companies', null=False)

    # Fee Rate Assessed for new cashflows as a percentage of USD value of flow (in decimal, so 1% = 0.01)
    # This is a one-time fee, when cashflows are added to an account
    new_cash_fee_rate = models.FloatField(null=False, validators=[MinValueValidator(0.0), MaxValueValidator(0.5)])

    # Annualized Fee Rate Assessed for Assets under management.
    # This is expressed as an annualized rate (in decimal, so 1% = 0.01)
    # If the rate is 0.01, then we will charged daily 0.01 / 365
    aum_fee_rate = models.FloatField(null=False, validators=[MinValueValidator(0.0), MaxValueValidator(0.5)])

    @staticmethod
    def create_tier(company: Company,
                    tier_from: float,
                    new_cash_fee_rate: float,
                    aum_fee_rate: float) -> 'FeeTier':
        if tier_from < 0:
            raise ValueError("Must have tier_from >= 0")

        tier = FeeTier(company=company, tier_from=tier_from,
                       new_cash_fee_rate=new_cash_fee_rate, aum_fee_rate=aum_fee_rate)
        tier.save()
        return tier

    @staticmethod
    def get_tier_for_aum_level(company: Company, aum_level: float) -> Optional['FeeTier']:
        filters = {'company': company,
                   'tier_from__lte': aum_level}

        objs = FeeTier.objects.filter(**filters).order_by('-tier_from')
        if len(objs) < 1:
            raise RuntimeError("No tiers found for company below the supplied level, should have tier at zero")

        return objs[0]

    @staticmethod
    def has_tiers(company: Company) -> bool:
        filters = {'company': company}

        objs = FeeTier.objects.filter(**filters)
        return len(objs) > 0

auditlog.register(FeeTier)
