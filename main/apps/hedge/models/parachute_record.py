from typing import Dict, Optional, List, Tuple

from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company, Account
from main.apps.currency.models.fxpair import FxPair

import logging

from main.apps.hedge.models import CompanyHedgeAction

logger = logging.getLogger(__name__)


# ==================
# Type definitions
# ==================

class ParachuteRecordAccount(models.Model):
    """
    A model that records the statistics for a month bucket of a particular parachute account.
    """

    class Meta:
        verbose_name_plural = "parachute_record_accounts"

    # The parachute account that the record is for.
    parachute_account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # The year, month bucket, yyyymm form
    bucket = models.IntegerField(null=False)

    # Company hedge action the record corresponds to.
    company_hedge_action = models.ForeignKey(CompanyHedgeAction, on_delete=models.CASCADE, null=False)

    # The limit value - the value that we do not want the bucket value fall below.
    limit_value = models.FloatField(null=False, default=0.)

    # The limit value plus the floating-limit pnl adjustment, which is a percentage of the max PnL the bucket has ever had.
    adjusted_limit_value = models.FloatField(null=False, default=0.)

    # The NPV of the cashflows, spot, and forwards in the bucket.
    #
    # Note that forward's value comes from PnL, since we entered into the forwards at 0.
    bucket_npv = models.FloatField(null=False, default=0.)

    # The probability target (lower p).
    p_limit = models.FloatField(null=False, default=0.)

    # The value (NPV) of just the cashflows in the bucket.
    cashflows_npv = models.FloatField(null=False, default=0.)

    # The pnl of all forwards for this bucket.
    forwards_pnl = models.FloatField(null=False, default=0.)

    # The realized pnl of spot positions for this bucket.
    realized_pnl = models.FloatField(null=False, default=0.)

    # The unrealized pnl of spot positions for this bucket.
    unrealized_pnl = models.FloatField(null=False, default=0.)

    # The *annualized* of the unhedged exposure volatility
    ann_volatility = models.FloatField(null=True, default=None)

    # The volatility over the time horizon (generally 1-day volatility).
    volatility = models.FloatField(null=True, default=None)

    # The probability that we *do not* breach over the next N days, N determined by the time horizon.
    p_no_breach = models.FloatField(null=True, default=0.)

    # The time horizon used for the p-calculation, in days.
    time_horizon = models.IntegerField(null=False, default=0)

    # The fraction that the bucket was instructed to hedge.
    fraction_to_hedge = models.FloatField(null=False, default=0.)

    # The sum of the absolute values of the remaining Fx exposures
    sum_abs_remaining = models.FloatField(null=False, default=-1.)

    # The net account PnL for the bucket.
    account_pnl = models.FloatField(null=False, default=0.)

    # The maximum PnL the bucket has ever had. Used for floating-limit parachute.
    #
    # The PnL is computed as compared to the initial account value.
    max_pnl = models.FloatField(null=False, default=0.)

    # We assume that parachute users (clients) have enough money set aside, or expected to come in from other cashflows,
    # that if parachute succeeds in keeping them above the threshold, they will be able to meet all their obligations.
    # We calculate here the minimum amount of cash that the client's cashflow imply that they must have on hand at the
    # beginning of running parachute.
    implied_minimum_client_cash = models.FloatField(null=False, default=0.)

    # We compute the PnL of the client's (implied) cash will accrue over the next one day.
    # This is not part of the client's implied cash PnL today, but it will be on the next day.
    forward_client_cash_one_day_pnl = models.FloatField(null=False, default=0.)

    # The cumulative PnL of the client's implied cash account.
    client_implied_cash_pnl = models.FloatField(null=False, default=0.)

    @property
    def bucket_value(self):
        """ Get the total value of the (hedged) bucket. """
        return self.cashflows_npv + self.forwards_pnl

    @property
    def complete_bucket_value(self):
        """ Get the bucket value, inclusive of client implied cash PnL. """
        return self.client_implied_cash_pnl + self.bucket_value

    def bucket_as_pair(self) -> Tuple[int, int]:
        return int(self.bucket / 100), self.bucket % 100

    @staticmethod
    def get(id):
        if isinstance(id, ParachuteRecordAccount):
            return id
        else:
            return ParachuteRecordAccount.objects.get(pk=id)

    @staticmethod
    def create_record(bucket: Tuple[int, int],  # year, month
                      parachute_account: Account,
                      company_hedge_action: CompanyHedgeAction,
                      bucket_npv: float,
                      limit_value: float,
                      adjusted_limit_value: float,
                      p_limit: float):
        bucket_int = bucket[0] * 100 + bucket[1]
        return ParachuteRecordAccount.objects.create(parachute_account=parachute_account,
                                                     bucket=bucket_int,
                                                     company_hedge_action=company_hedge_action,
                                                     bucket_npv=bucket_npv,
                                                     limit_value=limit_value,
                                                     adjusted_limit_value=adjusted_limit_value,
                                                     p_limit=p_limit)

    @staticmethod
    def get_last_record(parachute_account: Account, bucket, time: Date) -> Optional['ParachuteRecordAccount']:
        """ Get the last (of strictly less time) parachute account record. """
        obj = ParachuteRecordAccount.objects.filter(company_hedge_action__time__lt=time,
                                                    bucket=bucket,
                                                    parachute_account=parachute_account) \
            .order_by("-company_hedge_action__time")
        if not obj:
            return None
        return obj.first()

    @staticmethod
    def get_in_range(account: Account,
                     start_date: Optional[Date] = None,
                     end_date: Optional[Date] = None) -> List['ParachuteRecordAccount']:
        filters = {"parachute_account": Account.get_account(account=account)}
        if start_date:
            filters["company_hedge_action__time__gte"] = start_date
        if end_date:
            filters["company_hedge_action__time__lte"] = end_date
        return [x for x in ParachuteRecordAccount.objects.filter(**filters).order_by("company_hedge_action__time")]

    @staticmethod
    def get_in_range_bucketed(account: Account,
                              start_date: Optional[Date] = None,
                              end_date: Optional[Date] = None
                              ) -> Dict[Tuple[int, int], List['ParachuteRecordAccount']]:
        results = ParachuteRecordAccount.get_in_range(account=account, start_date=start_date, end_date=end_date)
        bucketed = {}
        for result in results:
            bucketed.setdefault(result.bucket_as_pair(), []).append(result)
        return bucketed

    @property
    def time(self) -> Date:
        return Date.from_datetime(self.company_hedge_action.time)


auditlog.register(ParachuteRecordAccount)
