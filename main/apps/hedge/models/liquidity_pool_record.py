from typing import Dict, Optional

from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company
from main.apps.currency.models.fxpair import FxPair

import logging

from main.apps.hedge.models import CompanyHedgeAction

logger = logging.getLogger(__name__)


# ==================
# Type definitions
# ==================


class LiquidityPoolRecord(models.Model):
    """
    A model that records the total exposure that a company had, as well as the amount of "liquidity pool useage."
    """

    # Company hedge action the liquidity pool record is associated with.
    company_hedge_action = models.ForeignKey(CompanyHedgeAction, on_delete=models.CASCADE, null=False)

    # The FX pair in which we have a position (these are always stored in the MARKET traded convention)
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, related_name='fxpair_lp_record', null=False)

    # Amount of this fx pair which was initially in the pool. This is the company's net exposure in this currency.
    total_exposure = models.FloatField(null=False, default=0.)

    # Amount of the pool that was used.
    pool_useage = models.FloatField(null=False, default=0.)

    # Whether this is for a company's live accounts as opposed to for the demo accounts.
    is_live = models.BooleanField(null=False)

    @staticmethod
    def make_records(company_hedge_action: CompanyHedgeAction,
                     exposures: Dict[FxPair, float],
                     useage: Dict[FxPair, float],
                     is_live: bool):
        new_records = []
        for fxpair in set(exposures.keys()).union(useage.keys()):
            record = LiquidityPoolRecord(company_hedge_action=company_hedge_action,
                                         fxpair=FxPair.get_pair(fxpair),
                                         total_exposure=exposures.get(fxpair, 0.),
                                         pool_useage=useage.get(fxpair, 0.),
                                         is_live=is_live)
            new_records.append(record)
        logger.debug(f"Creating {len(new_records)} new liquidity pool records, for {'live' if is_live else 'demo'} "
                    f"accounts associated with company hedge action {company_hedge_action.id}.")
        LiquidityPoolRecord.objects.bulk_create(new_records)

    @staticmethod
    def get_records_for_company(company: CompanyTypes,
                                start_time: Optional[Date] = None,
                                end_time: Optional[Date] = None):
        """
        Get all liquidity pool records for a company within a range.
        """
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)
        filters = {"company_hedge_action__company": company_}
        if start_time:
            filters["company_hedge_action__time__gte"] = start_time
        if end_time:
            filters["company_hedge_action__time__lte"] = end_time
        return LiquidityPoolRecord.objects.filter(**filters)


auditlog.register(LiquidityPoolRecord)
