import uuid
from typing import Optional, Tuple, Iterable, Union

from django.db import models
from django.db.models import QuerySet

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account, AccountTypes, CompanyTypes
from main.apps.util import ActionStatus


class BaseAccountSnapshot(models.Model):
    class Meta:
        abstract = True

    # The time at which the snapshot was taken.
    snapshot_time = models.DateTimeField(null=False)

    # The last snapshot for this account.
    last_snapshot = models.ForeignKey("self", on_delete=models.CASCADE, null=True, related_name="last")
    # The next snapshot for this account.
    next_snapshot = models.ForeignKey("self", on_delete=models.CASCADE, null=True, related_name="next")

    # The change in realized PnL due to Fx spot (of HEDGE positions) since the last snapshot.
    change_in_realized_pnl_fxspot = models.FloatField(null=False, default=0)
    # The change in realized PnL due to Fx forwards since the last snapshot.
    change_in_realized_pnl_fxforward = models.FloatField(null=False, default=0)
    # The total realized PnL (from everything - fx spot, fx forwards, etc.) for the account for all history.
    total_realized_pnl = models.FloatField(null=False, default=0)

    # The unrealized PnL of all current Fx spot positions.
    unrealized_pnl_fxspot = models.FloatField(null=False, default=0)
    # The unrealized PnL of all current Fx forward positions.
    unrealized_pnl_fxforward = models.FloatField(null=False, default=0)

    # A rough estimate of the "dollar theta" that the positions experienced since the last snapshot.
    #
    # This is derived by pricing the forwards, and pricing them again with a delivery date dT days later (dT being the
    # time between the last snapshot and now). We sum these differences over all fx forward positions
    fxforward_theta_approximate = models.FloatField(null=True, default=None)

    # The value of all positions the account holds, excluding domestic position.
    # Note that:
    #       directional_positions_value + domestic cash value = unrealized pnl
    directional_positions_value = models.FloatField(null=False, default=0)

    # The NPV of all the account's cashflows (looks into future an amount equal to max_horizon in hedge settings)
    cashflow_npv = models.FloatField(null=False, default=0)
    # The Sum of the absolute values of the NPVs of the account's cashflows.
    cashflow_abs_npv = models.FloatField(null=False, default=0)
    # Day-over-day change in NPV accounting for cashflows rolling on and off.
    change_in_npv = models.FloatField(null=False, default=0)

    # The value of taking forward Fx positions that perfectly cancels all cashflows.
    cashflow_fwd = models.FloatField(null=False, default=0)

    # The sum of the absolute values of the forwards of all cashflows.
    cashflow_abs_fwd = models.FloatField(null=False, default=0)

    # The final value (in domestic) of all cashflows that were paid between the last account snapshot and now.
    cashflow_roll_off = models.FloatField(null=False, default=0)
    # The NPV of all cashflows that were not within the max horizon at the time of the last snapshot, but are now.
    cashflow_roll_on = models.FloatField(null=False, default=0)
    # The number of cashflows that were paid between the last account snapshot and now.
    num_cashflows_rolled_off = models.IntegerField(null=False, default=0)
    # The number of cashflows that were not within max horizon at the time of the last snapshot, but are now.
    num_cashflows_rolled_on = models.IntegerField(null=False, default=0)
    # The number of cashflows that were within the max horizon.
    num_cashflows_in_window = models.IntegerField(null=False, default=0)

    # If cashflows were changed since the last snapshot, this is the difference in NPV of the original and final
    # set of cashflows, evaluated now.
    cashflow_meddling_adjustment = models.FloatField(null=True)

    # The total value (in domestic) of all cashflows that have rolled off during the lifetime of the account.
    total_cashflow_roll_off = models.FloatField(null=False, default=0)

    # The commission that was incurred on this day (attributed to this account), in the domestic currency.
    daily_commission = models.FloatField(null=False, default=0)
    # The commission that has been incurred over the lifetime of the account, in the domestic currency.
    cumulative_commission = models.FloatField(null=False, default=0)

    # The roll costs that was charged the account (negative) or credited to the account (positive) since the last
    # snapshot.
    daily_roll_value = models.FloatField(null=False, default=0)
    # The total roll costs that were charged or credited to the account since inception.
    cumulative_roll_value = models.FloatField(null=False, default=0)

    # The value of all trading that occurred today, in the domestic currency.
    daily_trading = models.FloatField(null=False, default=0)

    # The daily value of (unhedgedvalue_{T_k} - unhedgedvalue_{T_{k-1}}) ^ 2 / (T_k - T_{k-1})
    daily_unhedged_variance = models.FloatField(null=False, default=0)
    # The daily value of (hedgedvalue_{T_k} - hedgedvalue_{T_{k-1}}) ^ 2 / (T_k - T_{k-1})
    daily_hedged_variance = models.FloatField(null=False, default=0)

    # Value that the unhedged account would have, NPV of cashflows plus rolled off cashflows.
    unhedged_value = models.FloatField(null=False, default=0)
    # Value that the hedged account has, NPV of cashflows plus rolled off cashflows, plus PnL.
    hedged_value = models.FloatField(null=False, default=0)

    # Margin estimate for this account (based on fx positions), ignoring all other accounts
    margin = models.FloatField(null=False, default=0)


class AccountSnapshot(BaseAccountSnapshot):
    """
    Model that represents a snapshot of a single Pangea account's data.
    Since this is at the Pangea Account level, the data is driven by our own internal computing of an accounts
    positions.
    """

    class Meta:
        verbose_name_plural = "Account Snapshots"
        unique_together = (("account", "snapshot_time"),)

    # The account for which this is a snapshot.
    account = models.ForeignKey(Account, on_delete=models.CASCADE, null=False)

    # ============================================================
    # Properties.
    # ============================================================

    @property
    def unrealized_pnl(self):
        return self.unrealized_pnl_fxspot + self.unrealized_pnl_fxforward

    @property
    def change_in_realized_pnl(self):
        return self.change_in_realized_pnl_fxspot + self.change_in_realized_pnl_fxforward

    @property
    def meddling_adjustment_or_zero(self):
        """ Return the cashflow-meddling-adjustment if it is not None, or zero if it is. """
        return self.cashflow_meddling_adjustment if self.cashflow_meddling_adjustment else 0.

    # ============================================================
    # Accessors.
    # ============================================================

    @staticmethod
    def get_snapshot(snapshot: Union['AccountSnapshot', int]):
        if isinstance(snapshot, AccountSnapshot):
            return snapshot
        else:
            return AccountSnapshot.objects.get(pk=snapshot)

    @staticmethod
    def get_snapshots(company: Optional[CompanyTypes] = None,
                      account: Optional[AccountTypes] = None,
                      start_time: Optional[Date] = None,
                      end_time: Optional[Date] = None) -> QuerySet['AccountSnapshot']:
        filters = {}
        if account:
            filters["account"] = Account.get_account(account)
        elif company:
            filters["account__company"] = Company.get_company(company)

        if start_time:
            filters["snapshot_time__gte"] = start_time
        if end_time:
            filters["snapshot_time__lte"] = end_time

        return AccountSnapshot.objects.filter(**filters).order_by("snapshot_time")

    @staticmethod
    def get_snapshots_in_range_for_account(account: AccountTypes,
                                           start_time: Optional[Date] = None,
                                           end_time: Optional[Date] = None,
                                           ) -> QuerySet['AccountSnapshot']:
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)
        return AccountSnapshot.get_snapshots(account=account, start_time=start_time, end_time=end_time)

    # ============================================================
    # Mutators.
    # ============================================================

    @staticmethod
    def add_snapshot(account: AccountTypes,
                     change_in_realized_pnl: float,
                     total_realized_pnl: float,
                     unrealized_pnl: float,
                     directional_positions_value: float,
                     time: Optional[Date] = None) -> Tuple[ActionStatus, Optional['AccountSnapshot']]:
        account_ = Account.get_account(account)
        if not account_:
            return ActionStatus.log_and_error(f"Could not find account {account}."), None
        if not time:
            time = not Date.now()
        obj, created = AccountSnapshot.objects.get_or_create(account=account_,
                                                             snapshot_time=time,
                                                             change_in_realized_pnl=change_in_realized_pnl,
                                                             total_realized_pnl=total_realized_pnl,
                                                             unrealized_pnl=unrealized_pnl,
                                                             directional_positions_value=directional_positions_value
                                                             )
        if not created:
            return ActionStatus.log_and_no_change(f"Account snapshot already exists for account {account}."), obj
        return ActionStatus.log_and_success(f"Created account snapshot for account {account}"), obj


class CompanySnapshot(models.Model):
    """
    Model that represents a snapshot of company data
    This should contain data from broker (e.g. IB) for live account, since this is the actual base source of truth.
    For demo account data, this info may come from hedge positions and spot caches, etc.
    """

    # The company the snapshot is for.
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    # The time at which the snapshot was taken.
    snapshot_time = models.DateTimeField(null=False)

    # ========================================================================
    #  Values reported by the broker.
    # ========================================================================

    # Broker report of the total cash holding.
    #
    # If data cannot be found, the field is NaN.
    total_cash_holding = models.FloatField(null=True, default=None)

    # Broker report of the excess liquidity.
    #
    # If data cannot be found, the field is NaN.
    excess_liquidity = models.FloatField(null=True, default=None)

    # Broker report of the total maintenance margin.
    #
    # If data cannot be found, the field is NaN.
    total_maintenance_margin = models.FloatField(null=True, default=None)

    # Broker report of the total asset value.
    #
    # If data cannot be found, the field is NaN.
    total_asset_value = models.FloatField(null=True, default=None)

    # ========================================================================
    #  Other data.
    # ========================================================================

    # The sum of absolute values of all cashflows across all live accounts.
    live_cashflow_abs_fwd = models.FloatField(null=False, default=0)
    # The sum of absolute values of all cashflows across all demo accounts.
    demo_cashflow_abs_fwd = models.FloatField(null=False, default=0)

    # The sum of the number of cashflows within the time windows from each live account.
    num_live_cashflows_in_windows = models.IntegerField(null=False, default=0)
    # The sum of the number of cashflows within the time windows from each demo account.
    num_demo_cashflows_in_windows = models.IntegerField(null=False, default=0)

    # The last snapshot for this company.
    last_snapshot = models.ForeignKey("self", on_delete=models.CASCADE, null=True, related_name="last")
    # The next snapshot for this company.
    next_snapshot = models.ForeignKey("self", on_delete=models.CASCADE, null=True, related_name="next")

    # Theoretical roll value of the company's net positions.
    daily_roll_value = models.FloatField(null=False, default=0)

    # Total domestic value of positions for live accounts. This comes from CompanyFxPositions.
    live_position_value = models.FloatField(null=False, default=0.0)
    # Total domestic value of positions for demo accounts. This comes from CompanyFxPositions.
    demo_position_value = models.FloatField(null=False, default=0.0)

    demo_unrealized_pnl = models.FloatField(null=False, default=0.0)
    live_unrealized_pnl = models.FloatField(null=False, default=0.0)

    # The change in realized PnL (of HEDGE positions) since the last snapshot.
    live_change_in_realized_pnl = models.FloatField(null=False, default=0)
    demo_change_in_realized_pnl = models.FloatField(null=False, default=0)

    # The total realized PnL (of HEDGE positions) for the account for all history.
    live_total_realized_pnl = models.FloatField(null=False, default=0)
    demo_total_realized_pnl = models.FloatField(null=False, default=0)

    # ============================================================
    # Accessors.
    # ============================================================

    # ============================================================
    # Mutators.
    # ============================================================

    @staticmethod
    def create_snapshot(company: CompanyTypes,
                        time: Optional[Date] = None) -> 'CompanySnapshot':
        if not time:
            time = Date.now()

        company_ = Company.get_company(company)
        if not company_:
            raise ValueError(f"could not find company {company}")

        obj, created = CompanySnapshot.objects.get_or_create(company=company, snapshot_time=time)
        return obj


class AccountSnapshotTemplateData(BaseAccountSnapshot):
    template_name = models.CharField(max_length=100)
    template_id = models.BigIntegerField()
    template_uuid = models.SlugField(max_length=100)
    template_source = models.CharField(max_length=11)
    last_snapshot = models.BigIntegerField(null=True)


class CompanySnapshotConfiguration(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    account_id = models.BigIntegerField()
    template_uuid = models.CharField(max_length=100)

