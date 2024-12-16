from typing import Dict, Optional

import numpy as np

from hdlib.DateTime.Date import Date
from main.apps.account.models import AccountTypes, CompanyTypes
from main.apps.history.services.snapshot import SnapshotProvider


class HistoryProvider:
    def __init__(self, snapshot_provider: SnapshotProvider = SnapshotProvider()):
        self._snapshot_provider = snapshot_provider

    def get_account_performance(self,
                                account: AccountTypes,
                                start_date: Date,
                                end_date: Date) -> Dict[str, list]:
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end date ({end_date}) must be greater or equal to start date ({start_date})")
        snapshots = self._snapshot_provider.get_account_snapshots(account=account,
                                                                  start_date=start_date, end_date=end_date)

        initial_pnl = None
        times, unhedged_values, hedged_values, total_pnl, num_cashflows = [], [], [], [], []
        for snapshot in snapshots:
            times.append(Date.from_datetime(snapshot.snapshot_time))

            pnl = snapshot.total_realized_pnl + snapshot.unrealized_pnl_fxspot
            if not initial_pnl:
                initial_pnl = pnl

            unhedged_values.append(snapshot.unhedged_value)
            hedged_values.append(snapshot.hedged_value)
            total_pnl.append(pnl - initial_pnl)
            num_cashflows.append(snapshot.num_cashflows_in_window)

        return {
            "times": times,
            "unhedged": unhedged_values,
            "hedged": hedged_values,
            "pnl": total_pnl,
            "num_cashflows": num_cashflows
        }

    def get_account_pnl(self,
                        account: AccountTypes,
                        start_date: Date,
                        end_date: Date) -> Dict[str, list]:
        """
        Get the hedged and unhedged PnLs for an account. The PnL is measured since the accounts inception.
        """
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end date ({end_date}) must be greater or equal to start date ({start_date})")
        time, hedged_pnl, unhedged_pnl = self._snapshot_provider.get_account_pnl_ts(account=account,
                                                                                    start_date=start_date,
                                                                                    end_date=end_date)
        return {
            "times": time,
            "unhedged_pnl": unhedged_pnl,
            "hedged_pnl": hedged_pnl,
        }

    def get_total_account_performances(self,
                                       company: CompanyTypes,
                                       start_date: Date,
                                       end_date: Date):
        """
        Get the sum of the hedged, unhedged, and (total) PnL values of all live accounts and all demo accounts.
        """
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end date ({end_date}) must be greater or equal to start date ({start_date})")

        snapshots = self._snapshot_provider.get_account_snapshots(company=company, start_date=start_date,
                                                                  end_date=end_date)
        values_by_time, num_cashflows_by_time = {}, {}
        for snapshot in snapshots:
            time = Date.from_datetime(snapshot.snapshot_time)
            if time not in values_by_time:
                # Add entries for {hedged live, unhedged live, live PnL, hedged demo, unhedged demo, demo PnL} values.
                values_by_time[time] = np.array([0., 0., 0., 0., 0., 0.])
                num_cashflows_by_time[time] = np.array([0, 0])

            total_pnl = snapshot.total_realized_pnl + snapshot.unrealized_pnl_fxspot
            if snapshot.account.is_live_account:
                values_by_time[time] += np.array([snapshot.hedged_value, snapshot.unhedged_value, total_pnl,
                                                  0., 0., 0.])
                num_cashflows_by_time[time] += np.array([snapshot.num_cashflows_in_window, 0])
            elif snapshot.account.is_active:
                values_by_time[time] += np.array([0., 0., 0.,
                                                  snapshot.hedged_value, snapshot.unhedged_value, total_pnl])
                num_cashflows_by_time[time] += np.array([0, snapshot.num_cashflows_in_window])

        # Subtract away the initial values.
        initial_values = None
        times, hedged_live, unhedged_live, pnl_live, hedged_demo, unhedged_demo, pnl_demo, \
        live_num_cashflows, demo_num_cashflows = [[] for _ in range(9)]
        for time, values in values_by_time.items():
            if initial_values is None:
                initial_values = values
            adjusted_vals = values - initial_values
            times.append(time)
            hedged_live.append(values[0])  # adjusted_vals[0])
            unhedged_live.append(values[1])  # adjusted_vals[1])
            pnl_live.append(adjusted_vals[2])
            hedged_demo.append(values[3])  # adjusted_vals[3])
            unhedged_demo.append(values[4])  # adjusted_vals[4])
            pnl_demo.append(adjusted_vals[5])

            live_num, demo_num = num_cashflows_by_time[time]
            live_num_cashflows.append(live_num)
            demo_num_cashflows.append(demo_num)

        return {
            "times": times,
            "live_hedged": hedged_live,
            "live_unhedged": unhedged_live,
            "live_pnl": pnl_live,
            "demo_hedged": hedged_demo,
            "demo_unhedged": unhedged_demo,
            "demo_pnl": pnl_demo,
            "live_num_cashflows": live_num_cashflows,
            "demo_num_cashflows": demo_num_cashflows,
        }

    # noinspection DuplicatedCode
    def get_cashflow_abs_forward(self,
                                 start_date: Date,
                                 end_date: Date,
                                 company: Optional[CompanyTypes] = None,
                                 account: Optional[AccountTypes] = None
                                 ):
        if start_date and end_date and end_date < start_date:
            raise ValueError(f"end date ({end_date}) must be greater or equal to start date ({start_date})")
        if company is None and account is None:
            raise ValueError(f"one of company and account must not be None")

        if company is None:
            # Get abs forward for an account.
            snapshots = self._snapshot_provider.get_account_snapshots(account=account, start_date=start_date,
                                                                      end_date=end_date)
            values_by_time = {}
            for snapshot in snapshots:
                time = Date.from_datetime(snapshot.snapshot_time)
                values_by_time[time] = (snapshot.cashflow_abs_fwd, snapshot.num_cashflows_in_window)

            times, values, numbers = [], [], []
            for time, (value, num) in values_by_time.items():
                times.append(time)
                values.append(value)
                numbers.append(num)

            return {
                "times": times,
                "cashflow_abs_fwd": values,
                "num_cashflows": numbers
            }
        else:
            # Get abs forward for a company.
            snapshots = self._snapshot_provider.get_company_snapshots(company=company, start_date=start_date,
                                                                      end_date=end_date)
            values_by_time = {}
            for snapshot in snapshots:
                time = Date.from_datetime(snapshot.snapshot_time)
                values_by_time[time] = (snapshot.live_cashflow_abs_fwd, snapshot.demo_cashflow_abs_fwd,
                                        snapshot.num_live_cashflows_in_windows, snapshot.num_demo_cashflows_in_windows)

            times, live_cashflow_abs_fwd, demo_cashflow_abs_fwd, live_number, demo_number = [], [], [], [], []
            for time, (live_fwd, demo_fwd, live_num, demo_num) in values_by_time.items():
                times.append(time)
                live_cashflow_abs_fwd.append(live_fwd)
                demo_cashflow_abs_fwd.append(demo_fwd)
                live_number.append(live_num)
                demo_number.append(demo_num)

            return {"times": times,
                    "live_cashflow_abs_fwd": live_cashflow_abs_fwd,
                    "demo_cashflow_abs_fwd": demo_cashflow_abs_fwd,
                    "live_num_cashflows": live_number,
                    "demo_num_cashflows": demo_number,
                    }
