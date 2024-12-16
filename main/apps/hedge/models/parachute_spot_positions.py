from typing import Dict, Optional, List, Tuple

import numpy as np
from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company, Account
from main.apps.currency.models import Currency
from main.apps.currency.models.fxpair import FxPair

import logging

from main.apps.hedge.models import CompanyHedgeAction

logger = logging.getLogger(__name__)


# ==================
# Type definitions
# ==================

class ParachuteSpotPositions(models.Model):
    """
    A model that records how spot positions are associated with each parachute bucket.
    """

    class Meta:
        verbose_name_plural = "parachute_record_accounts"

    # The parachute account that the record is for.
    parachute_account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # The year, month bucket, yyyymm form
    bucket = models.IntegerField(null=False)

    # Company hedge action the record corresponds to.
    company_hedge_action = models.ForeignKey(CompanyHedgeAction, on_delete=models.CASCADE, null=False)

    # The Fx pair that this position is for.
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)

    # The amount of this position, associated with this bucket.
    amount = models.FloatField(null=False, default=0.)

    # Total price for the entire position (always positive), in the quote currency: sum_i (|Q_i| * Spot(t_i))
    # Note that trades in the opposite direction of the current amount will reduce the total price.
    #
    # Note: We make total price always positive to follow the convention of FxPosition.
    total_price = models.FloatField(null=False, default=0.)

    def bucket_as_pair(self) -> Tuple[int, int]:
        return int(self.bucket / 100), self.bucket % 100

    def unrealized_pnl(self, current_rate: float) -> Tuple[float, Currency]:
        """
        Retrieve the unrealized PnL in the quote currency
        :param current_rate: float, the current FX rate corresponding to this position
        :return: [PnL, Currency], the unrealized pnl of this position at the current rate
        """
        if self.amount == 0:
            return 0.0, self.fxpair.quote_currency
        return self.amount * current_rate - np.sign(self.amount) * self.total_price, self.fxpair.quote_currency

    @staticmethod
    def create_record(bucket: Tuple[int, int],  # year, month
                      parachute_account: Account,
                      company_hedge_action: CompanyHedgeAction,
                      fxpair: FxPair,
                      amount: float,
                      total_price: float) -> 'ParachuteSpotPositions':
        if isinstance(bucket, int):
            bucket_int = bucket
        else:
            bucket_int = bucket[0] * 100 + bucket[1]
        return ParachuteSpotPositions.objects.create(parachute_account=parachute_account,
                                                     bucket=bucket_int,
                                                     company_hedge_action=company_hedge_action,
                                                     fxpair=fxpair,
                                                     amount=amount,
                                                     total_price=total_price)

    @staticmethod
    def get_last_record(parachute_account: Account,
                        bucket: int,
                        fxpair: FxPair,
                        time: Date) -> Optional['ParachuteSpotPositions']:
        """ Get the last (of strictly less time) parachute account record. """
        obj = ParachuteSpotPositions.objects.filter(company_hedge_action__time__lt=time,
                                                    bucket=bucket,
                                                    fxpair=fxpair,
                                                    parachute_account=parachute_account) \
            .order_by("-company_hedge_action__time")
        if not obj:
            return None
        return obj.first()

    @staticmethod
    def get_all_last_records(parachute_account: Account,
                             time: Date) -> List['ParachuteSpotPositions']:
        """
        Get the last (of strictly less time) parachute account records for the account, for all buckets and pairs.
        """
        # Get the last company hedge action.
        obj = ParachuteSpotPositions.objects.filter(company_hedge_action__time__lt=time,
                                                    parachute_account=parachute_account) \
            .order_by("-company_hedge_action__time")
        if not obj:
            return []
        hedge_action = obj.first().company_hedge_action
        return ParachuteSpotPositions.objects.filter(company_hedge_action=hedge_action)

    @staticmethod
    def get_in_range(account: Account,
                     start_date: Optional[Date] = None,
                     end_date: Optional[Date] = None) -> List['ParachuteSpotPositions']:
        filters = {"parachute_account": Account.get_account(account=account)}
        if start_date:
            filters["company_hedge_action__time__gte"] = start_date
        if end_date:
            filters["company_hedge_action__time__lte"] = end_date
        return [x for x in ParachuteSpotPositions.objects.filter(**filters).order_by("company_hedge_action__time")]

    @staticmethod
    def get_in_range_bucketed(account: Account,
                              start_date: Optional[Date] = None,
                              end_date: Optional[Date] = None
                              ) -> Dict[Tuple[int, int], List['ParachuteSpotPositions']]:
        results = ParachuteSpotPositions.get_in_range(account=account, start_date=start_date, end_date=end_date)
        bucketed = {}
        for result in results:
            bucketed.setdefault(result.bucket_as_pair(), []).append(result)
        return bucketed

    @property
    def time(self) -> Date:
        return Date.from_datetime(self.company_hedge_action.time)


auditlog.register(ParachuteSpotPositions)
