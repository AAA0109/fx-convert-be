from typing import Optional, Tuple, List, Sequence

import numpy as np

from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company, Account, AccountTypes
from main.apps.broker.models import Broker
from main.apps.history.models.snapshot import CompanySnapshot, AccountSnapshot
from main.apps.util import get_or_none
from main.apps.history.support.snapshot_summary_stats import SnapshotSummaryStats

import logging

logger = logging.getLogger(__name__)


class SnapshotProvider(object):
    """
    Service for providing existing company / account snapshots
    """

    @get_or_none
    def get_last_account_snapshot(self,
                                  account: AccountTypes,
                                  date: Optional[Date] = None) -> AccountSnapshot:
        """
        Get the last snapshot for an account (overall, or on/before some supplied date)
        :param account: the account
        :param date: Date (optional), if supplied then get the latest snapshot on or before this date
        :return: AccountSnapshot if found, else None
        """
        if date is None:
            date = Date.now()

        account_ = Account.get_account(account)
        if not account_:
            raise ValueError(f"could not find account {account} and therefore can't get its last snapshot")
        return AccountSnapshot.objects.filter(account=account_, snapshot_time__lt=date) \
            .order_by("-snapshot_time").first()

    @get_or_none
    def get_last_company_snapshot(self,
                                  company: CompanyTypes,
                                  date: Optional[Date] = None) -> CompanySnapshot:
        """
        Get the last snapshot for a company (overall, or on/before some supplied date)
        :param company: the company
        :param date: Date (optional), if supplied then get the latest snapshot on or before this date
        :return: CompanySnapshot if found, else None
        """
        if date is None:
            date = Date.now()

        company_ = Company.get_company(company)
        if not Company:
            raise ValueError(f"could not find company {company} and therefore can't get its last snapshot")
        return CompanySnapshot.objects.filter(company=company_, snapshot_time__lte=date) \
            .order_by("-snapshot_time").first()

    def get_account_snapshots(self,
                              account: Optional[AccountTypes] = None,
                              company: Optional[CompanyTypes] = None,
                              start_date: Optional[Date] = None,
                              end_date: Optional[Date] = None) -> Sequence[AccountSnapshot]:
        """
        Get account snapshots for an account, or for all the accounts in a company, within a range of dates.

        :param account: Optional[AccountTypes], the account
        :param company: Optional[CompanyTypes], the company
        :param start_date: Date (optional), if supplied then only include snapshots on/after this date
        :param end_date: Date (optional), if supplied then only include snapshots on/before this date
        :return: sequence of AccountSnapshot, ordered by snapshot time.
        """
        if account is None and company is None:
            raise ValueError(f"either account or company must not be None to get_account_snapshots")

        filters = {}

        # Get the company or account.
        if company:
            company_ = Company.get_company(company)
            if not company_:
                raise Company.NotFound(company)
            filters["account__company"] = company_
        elif account:
            account_ = Account.get_account(account)
            if not account_:
                raise Account.NotFound(account)
            filters["account"] = account_

        if start_date:
            filters["snapshot_time__gte"] = start_date.start_of_day()
        if end_date:
            filters["snapshot_time__lte"] = end_date.start_of_next_day()
        return AccountSnapshot.objects.filter(**filters).order_by("snapshot_time")

    def get_company_snapshots(self,
                              company: CompanyTypes,
                              start_date: Optional[Date] = None,
                              end_date: Optional[Date] = None) -> Sequence[CompanySnapshot]:
        """
        Get snapshots for a company in a range of dates
        :param company: CompanyTypes, the account
        :param start_date: Date (optional), if supplied then only include snapshots on/after this date
        :param end_date: Date (optional), if supplied then only include snapshots on/before this date
        :return: sequence of AccountSnapshot
        """
        company_ = Company.get_company(company)
        if not company_:
            raise ValueError(f"could not find account {company} and therefore can't get its last snapshot")
        filters = {"company": company_}
        if start_date:
            filters["snapshot_time__gte"] = start_date.start_of_day()
        if end_date:
            filters["snapshot_time__lte"] = end_date.start_of_next_day()
        return CompanySnapshot.objects.filter(**filters).order_by("snapshot_time")

    def get_account_summary_stats(self,
                                  account: AccountTypes,
                                  start_date: Optional[Date] = None,
                                  end_date: Optional[Date] = None) -> Optional[SnapshotSummaryStats]:
        """
        Get summary stats based on account snapshots over a range of dates
        :param account: the account
        :param start_date: Date (optional), if supplied then only include snapshots on/after this date
        :param end_date: Date (optional), if supplied then only include snapshots on/before this date
        :return: SummaryStats, if there are at least 2 snapshots found, else None
        """
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots or len(snapshots) < 2:
            return None

        dc = DayCounter_HD()
        T = dc.year_fraction(start_date, end_date)

        snap_0 = snapshots[0]
        snap_T = snapshots[len(snapshots) - 1]

        # Get total realized variance of hedged vs unhedged
        variance_of_hedged, variance_of_unhedged = 0, 0
        for snap in snapshots:
            variance_of_hedged += snap.daily_hedged_variance
            variance_of_unhedged += snap.daily_unhedged_variance

        variance_of_hedged *= T
        variance_of_unhedged *= T

        # Compute total roll cost
        roll = snap_T.cumulative_roll_value - snap_0.cumulative_roll_value + snap_0.daily_roll_value

        stats = SnapshotSummaryStats(company=snap_0.account.company.name,
                                     summary_name=snap_0.account.name,
                                     start_date=Date.from_datetime(snap_0.snapshot_time),
                                     end_date=Date.from_datetime(snap_T.snapshot_time),
                                     initial_cash_npv=snap_0.cashflow_npv,
                                     remaining_cash_npv=snap_T.cashflow_npv,
                                     initial_hedge_value=snap_0.directional_positions_value,
                                     remaining_hedge_value=snap_T.directional_positions_value,
                                     final_hedged_value=snap_T.hedged_value,
                                     final_unhedged_value=snap_T.unhedged_value,
                                     realized_hedge_pnl=snap_T.total_realized_pnl - snap_0.total_realized_pnl,
                                     unrealized_hedge_pnl=snap_T.unrealized_pnl_fxspot - snap_0.unrealized_pnl_fxspot,
                                     variance_of_hedged=variance_of_hedged,
                                     variance_of_unhedged=variance_of_unhedged,
                                     total_cashflows_recieved=snap_T.total_cashflow_roll_off - snap_0.total_cashflow_roll_off,
                                     margin_start=snap_0.margin,
                                     margin_end=snap_T.margin,
                                     roll_costs=roll
                                     )
        return stats

    # ==========================================================
    #  Time-Series Accessors
    # ==========================================================

    def get_cumulative_variance_ts(self,
                                   account: AccountTypes,
                                   start_date: Date,
                                   end_date: Date) -> Tuple[np.array, np.array, np.array]:
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], [], []
        time, hedged_var, unhedged_var = [], [], []
        cumulative_hedged_var, cumulative_unhedged_var = 0, 0
        for snapshot in snapshots:
            # Update cumulative Vars
            cumulative_hedged_var += snapshot.daily_hedged_variance
            cumulative_unhedged_var += snapshot.daily_unhedged_variance

            # Extend the time series
            time.append(Date.from_datetime(snapshot.snapshot_time))
            hedged_var.append(cumulative_hedged_var)
            unhedged_var.append(cumulative_unhedged_var)
        return np.array(time), np.array(hedged_var), np.array(unhedged_var)

    @staticmethod
    def get_daily_variances_ts(account: AccountTypes,
                               start_date: Optional[Date] = None,
                               end_date: Optional[Date] = None) -> Tuple[np.array, np.array, np.array]:
        snapshots = SnapshotProvider()._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], [], []
        time, hedged_var, unhedged_var = [], [], []
        for snapshot in snapshots:
            time.append(snapshot.snapshot_time)
            hedged_var.append(snapshot.daily_hedged_variance)
            unhedged_var.append(snapshot.daily_unhedged_variance)
        return np.array(time), np.array(hedged_var), np.array(unhedged_var)

    @staticmethod
    def get_variance_reduction_ts(self,
                                  account: AccountTypes,
                                  start_date: Date,
                                  end_date: Date) -> Tuple[np.array, np.array]:
        dates, hedged_var, unhedged_var = self.get_cumulative_variance_ts(account, start_date, end_date)
        indicator = 0 < unhedged_var
        return dates[indicator], (1.0 - hedged_var / unhedged_var)[indicator]

    def get_cumulative_volatility_ts(self,
                                     account: AccountTypes,
                                     start_date: Date,
                                     end_date: Date) -> Tuple[np.array, np.array, np.array]:
        dates, hedged_var, unhedged_var = self.get_cumulative_variance_ts(account=account,
                                                                          start_date=start_date,
                                                                          end_date=end_date)
        return dates, np.sqrt(hedged_var), np.sqrt(unhedged_var)

    def get_volatility_reduction_ts(self,
                                    account: AccountTypes,
                                    start_date: Optional[Date] = None,
                                    end_date: Optional[Date] = None) -> Tuple[np.array, np.array]:
        dates, hedged_vol, unhedged_vol = self.get_cumulative_volatility_ts(account=account,
                                                                            start_date=start_date,
                                                                            end_date=end_date)
        indicator = 0 < unhedged_vol
        return dates[indicator], (1.0 - hedged_vol[indicator] / unhedged_vol[indicator])

    def get_account_hedged_value_ts(self,
                                    account: AccountTypes,
                                    start_date: Optional[Date] = None,
                                    end_date: Optional[Date] = None) -> Tuple[List[Date], List[float]]:
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], []
        time, value = [], []
        for snapshot in snapshots:
            time.append(Date.from_datetime(snapshot.snapshot_time))
            value.append(snapshot.hedged_value)
        return time, value

    def get_account_unhedged_value_ts(self,
                                      account: AccountTypes,
                                      start_date: Optional[Date] = None,
                                      end_date: Optional[Date] = None) -> Tuple[List[Date], List[float]]:
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], []
        time, value = [], []
        for snapshot in snapshots:
            time.append(Date.from_datetime(snapshot.snapshot_time))
            value.append(snapshot.unhedged_value)
        return time, value

    def get_account_cashflow_abs_npv_ts(self,
                                        account: AccountTypes,
                                        start_date: Optional[Date] = None,
                                        end_date: Optional[Date] = None) -> Tuple[List[Date], List[float]]:
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], []
        time, value = [], []
        for snapshot in snapshots:
            time.append(Date.from_datetime(snapshot.snapshot_time))
            value.append(snapshot.cashflow_abs_npv)
        return time, value

    def get_account_cashflow_fwd_ts(self,
                                    account: AccountTypes,
                                    start_date: Optional[Date] = None,
                                    end_date: Optional[Date] = None) -> Tuple[List[Date], List[float]]:
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], []
        time, value = [], []
        for snapshot in snapshots:
            time.append(Date.from_datetime(snapshot.snapshot_time))
            value.append(snapshot.cashflow_fwd)
        return time, value

    def get_account_unrealized_pnls_ts(self,
                                       account: AccountTypes,
                                       start_date: Optional[Date] = None,
                                       end_date: Optional[Date] = None) -> Tuple[List[Date], List[float], List[float]]:
        """
        Get the time series of spot and Fx unrealized pnls.
        """
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], [], []
        time, spot_pnl, forward_pnl = [], [], []
        for snapshot in snapshots:
            time.append(Date.from_datetime(snapshot.snapshot_time))
            spot_pnl.append(snapshot.unrealized_pnl_fxspot)
            forward_pnl.append(snapshot.unrealized_pnl_fxforward)

        return time, spot_pnl, forward_pnl

    def get_adjusted_account_value_ts(self,
                                      account: AccountTypes,
                                      start_date: Optional[Date] = None,
                                      end_date: Optional[Date] = None):
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)
        snapshots = self.get_account_snapshots(account=account_, start_date=start_date, end_date=end_date)

        dates, costs, placed_cashflow_rolloff, placed_pnl, placed_npv, adjusted_by_roll_on = [], [], [], [], [], []

        for snapshot in snapshots:
            dates.append(Date.from_datetime(snapshot.snapshot_time))
            costs.append(snapshot.cumulative_roll_value + snapshot.cumulative_commission)
            placed_cashflow_rolloff.append(costs[-1] + snapshot.total_cashflow_roll_off)
            pnl = snapshot.total_realized_pnl + snapshot.unrealized_pnl_fxspot

            placed_pnl.append(placed_cashflow_rolloff[-1] + pnl)
            placed_npv.append(placed_pnl[-1] + snapshot.cashflow_npv)
            # Note that this will calculate the *cumulative* roll off, not the amount yet to roll off.
            adjusted_by_roll_on.append(
                (adjusted_by_roll_on[-1] if 0 < len(adjusted_by_roll_on) else 0) + snapshot.cashflow_roll_on)

        total_roll_on = adjusted_by_roll_on[-1]
        for i in range(len(adjusted_by_roll_on)):
            adjusted_by_roll_on[i] = -(adjusted_by_roll_on[i] - total_roll_on) + placed_npv[i]

        return dates, adjusted_by_roll_on

    def get_account_pnl_ts(self,
                           account: AccountTypes,
                           start_date: Optional[Date] = None,
                           end_date: Optional[Date] = None) -> Tuple[List[Date], List[float], List[float]]:
        """
        Return the hedged and unhedged PnL, calculated by taking the difference between the hedged and unhedged account
        values and the original hedge and unhedged account values.
        """
        snapshots = self._get_validate(account, start_date, end_date)
        if not snapshots:
            return [], [], []
        time, hedged_pnl, unhedged_pnl = [], [], []

        # Get the first snapshot for this account from AccountSnapshot
        first_snapshot = AccountSnapshot.objects.filter(account=account).order_by('snapshot_time').first()
        # There is always a first snapshot, since we were already able to get snapshots for this account.
        # Get the original hedged and unhedged values from the first snapshot.
        original_hedged_value = first_snapshot.hedged_value
        original_unhedged_value = first_snapshot.unhedged_value

        for snapshot in snapshots:
            time.append(Date.from_datetime(snapshot.snapshot_time))
            hedged_pnl.append(snapshot.hedged_value - original_hedged_value)
            unhedged_pnl.append(snapshot.unhedged_value - original_unhedged_value)

        return time, hedged_pnl, unhedged_pnl

    def get_company_account_snapshots_by_date(self, company: CompanyTypes, start_date: Date, end_date: Date):
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)
        snapshots = AccountSnapshot.objects.filter(snapshot_time__gte=start_date,
                                                   snapshot_time__lte=end_date,
                                                   account__company=company_)
        output = {}
        for snapshot in snapshots:
            time = Date.from_datetime(snapshot.snapshot_time)
            output.setdefault(time, []).append(snapshot)
        return output

    def get_company_value_ts(self,
                             company: CompanyTypes,
                             start_date: Date,
                             end_date: Date) -> Tuple[List[Date], List[float]]:
        snapshots_by_date = self.get_company_account_snapshots_by_date(company=company,
                                                                       start_date=start_date,
                                                                       end_date=end_date)
        times, values = [], []
        for time, snapshots in snapshots_by_date.items():
            times.append(time)
            value = 0.0
            for snapshot in snapshots:
                value += snapshot.hedged_value
            values.append(value)
        return times, values

    def get_company_cashflow_abs_npv_ts(self,
                                        company: CompanyTypes,
                                        start_date: Date,
                                        end_date: Date) -> Tuple[List[Date], List[float]]:
        snapshots_by_date = self.get_company_account_snapshots_by_date(company=company,
                                                                       start_date=start_date,
                                                                       end_date=end_date)
        times, values = [], []
        for time, snapshots in snapshots_by_date.items():
            times.append(time)
            value = 0.0
            for snapshot in snapshots:
                value += snapshot.cashflow_abs_npv
            values.append(value)
        return times, values

    def _get_validate(self,
                      account: AccountTypes, start_date: Optional[Date], end_date: Optional[Date]):
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end date ({end_date}) must be greater or equal to start date ({start_date})")
        return self.get_account_snapshots(account=account, start_date=start_date, end_date=end_date)
