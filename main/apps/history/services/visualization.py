from typing import Optional, Iterable

import numpy as np
from hdlib.DateTime.Date import Date

from main.apps.account.models import AccountTypes, Account, CompanyTypes
from main.apps.hedge.services.liquidity_pool import LiquidityPoolService
from main.apps.history.services.snapshot import SnapshotProvider

try:
    from matplotlib import pyplot as plt
except:
    pass


class SnapshotVisualizationService(object):
    def __init__(self, snapshot_provider: SnapshotProvider = SnapshotProvider()):
        self._snapshot_provider = snapshot_provider

    def create_account_allocation_plot(self,
                                       account: AccountTypes,
                                       start_date: Optional[Date] = None,
                                       end_date: Optional[Date] = None):
        """
        Return a figure of the allocation plot.
        """
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)

        snapshots = self._snapshot_provider.get_account_snapshots(account=account_, start_date=start_date,
                                                                  end_date=end_date)
        if len(snapshots) == 0:
            return

        dates, costs, placed_cashflow_rolloff, placed_pnl, placed_npv, adjusted_by_roll_on = [], [], [], [], [], []

        for snapshot in snapshots:
            dates.append(snapshot.snapshot_time)
            costs.append(snapshot.cumulative_roll_value + snapshot.cumulative_commission)
            placed_cashflow_rolloff.append(costs[-1] + snapshot.total_cashflow_roll_off)
            pnl = snapshot.total_realized_pnl + snapshot.unrealized_pnl

            placed_pnl.append(placed_cashflow_rolloff[-1] + pnl)
            placed_npv.append(placed_pnl[-1] + snapshot.cashflow_npv)
            # Note that this will calculate the *cumulative* roll off, not the amount yet to roll off.
            adjusted_by_roll_on.append(
                (adjusted_by_roll_on[-1] if 0 < len(adjusted_by_roll_on) else 0) + snapshot.cashflow_roll_on)

        total_roll_on = adjusted_by_roll_on[-1]
        for i in range(len(adjusted_by_roll_on)):
            adjusted_by_roll_on[i] = -(adjusted_by_roll_on[i] - total_roll_on) + placed_npv[i]

        # Convert lists to arrays so the "where" can work in fill between.
        placed_pnl = np.array(placed_pnl)
        placed_cashflow_rolloff = np.array(placed_cashflow_rolloff)

        fig = plt.figure(figsize=(12, 8), dpi=100)
        subplot = fig.add_subplot()

        subplot.plot(dates, costs, linestyle="--", color="black", label="Cumulative costs (roll and commission)")
        subplot.fill_between(dates, costs, placed_cashflow_rolloff, color="lightgray",
                             label="Net cashflows paid/received")
        subplot.plot(dates, placed_cashflow_rolloff, color="black", label="Net cashflows + costs")

        subplot.fill_between(dates, placed_cashflow_rolloff, placed_pnl, where=(placed_pnl > placed_cashflow_rolloff),
                             color='green', alpha=0.9, interpolate=True, label="Positive total PnL")

        subplot.plot(dates, placed_pnl, color="blue", label="Total PnL + net cashflows + costs")
        subplot.fill_between(dates, placed_pnl, placed_npv, color="lightblue", label="Cashflow NPV")

        # Have to put this after the pnl-npv fill, so it can overwrite it.
        subplot.fill_between(dates, placed_cashflow_rolloff, placed_pnl, where=(placed_pnl <= placed_cashflow_rolloff),
                             color='darkblue', alpha=0.3, interpolate=True, label="Negative total PnL")

        subplot.plot(dates, placed_npv, color="black", label="Total account value")

        # Calculate some shading region?
        subplot.fill_between(dates, placed_npv, adjusted_by_roll_on,  # where=(placed_pnl <= placed_cashflow_rolloff),
                             color='moccasin', alpha=0.3, interpolate=True)

        subplot.plot(dates, adjusted_by_roll_on, color="orange", label="Total account value adjusted by roll on")

        # Titles and labels and such.
        subplot.legend()
        subplot.set_xlabel("Date")
        subplot.set_ylabel(f"Values ({account_.company.currency})")
        subplot.set_title(f"Account values history for {account_} (id={account_.id})")

        return fig

    def create_accounts_values_figure(self,
                                      company: Optional[CompanyTypes] = None,
                                      accounts: Optional[Iterable[AccountTypes]] = None,
                                      start_date: Optional[Date] = None,
                                      end_date: Optional[Date] = None,
                                      plot_starting_values: bool = True):
        accounts_ = self._get_accounts(company=company, accounts=accounts)

        fig = plt.figure(figsize=[15, 10])
        subplot = fig.add_subplot()

        starts, max_date = {}, None
        max_ls, linestyles = 10, ["-", "--", ":"]  # "constants"
        for it, account in enumerate(accounts_):
            date, value = self._snapshot_provider.get_account_hedged_value_ts(account=account,
                                                                              start_date=start_date,
                                                                              end_date=end_date)
            if 0 < len(date):
                subplot.plot(date, value, label=f"{account}", linestyle=linestyles[int(it / max_ls) % 3])

                max_date = date[-1] if max_date is None else np.maximum(max_date, date[-1])

                if plot_starting_values:
                    initial_value = np.round(value[0], decimals=2)
                    if initial_value in starts:
                        starts[initial_value] = np.minimum(starts[initial_value], date[0])
                    else:
                        starts[initial_value] = date[0]

        if plot_starting_values:
            for value, start_date in starts.items():
                subplot.plot([start_date, max_date], [value, value], color="black", linestyle=":")

        fig.legend()
        subplot.set_xlabel("Date")
        subplot.set_ylabel("Account value")
        subplot.set_title("Account hedged values")

        return fig

    def create_accounts_risk_reduction_figure(self,
                                              company: Optional[CompanyTypes] = None,
                                              accounts: Optional[Iterable[AccountTypes]] = None,
                                              start_date: Optional[Date] = None,
                                              end_date: Optional[Date] = None):
        accounts_ = self._get_accounts(company=company, accounts=accounts)

        fig = plt.figure(figsize=[15, 10])
        subplot = fig.add_subplot()

        max_ls, linestyles = 10, ["-", "--", ":"]  # "constants"
        for it, account in enumerate(accounts_):
            times, reduction = self._snapshot_provider.get_volatility_reduction_ts(account=account,
                                                                                   start_date=start_date,
                                                                                   end_date=end_date)
            subplot.plot(times, 100.0 * reduction, label=f"{account}", linestyle=linestyles[int(it / max_ls) % 3])

        fig.legend()
        subplot.set_xlabel("Date")
        subplot.set_ylabel("Reduction (%)")
        subplot.set_title("Reduction in realized volatility")

        return fig

    def create_realized_variance_figure(self,
                                        account: AccountTypes,
                                        start_date: Optional[Date] = None,
                                        end_date: Optional[Date] = None):
        t, h, u = self._snapshot_provider.get_cumulative_volatility_ts(account=account, start_date=start_date,
                                                                       end_date=end_date)
        fig = plt.figure(figsize=[12, 8])
        subplot = fig.add_subplot()

        subplot.plot(t, h, label="Hedged realized volatility")
        subplot.plot(t, u, label="Unhedged realized volatility")
        plt.legend()
        subplot.set_xlabel("Date")
        subplot.set_ylabel("Realized volatility")
        subplot.set_title("Realized variances")

        return fig

    def create_liquidity_pool_utilization_figure(self,
                                                 account: AccountTypes,
                                                 start_date: Optional[Date] = None,
                                                 end_date: Optional[Date] = None):
        utilization = LiquidityPoolService.get_pool_utilization(account=account,
                                                                start_date=start_date,
                                                                end_date=end_date)
        transposition = {}
        for hedge_action, utilizations in utilization.items():
            time = Date.from_datetime(hedge_action.time)
            for fxpair, utilization in utilizations.items():
                transposition.setdefault(fxpair, []).append((time, utilization))

        fig = plt.figure(figsize=(12, 8))
        for fxpair, time_series in transposition.items():
            t, v = zip(*sorted(time_series))
            plt.plot(t, v, label=f"Time series for {fxpair}")
        plt.legend()
        plt.title(f"Liquidity pool utilization for account {account}")
        plt.xlabel(f"Date")
        plt.ylabel(f"Amount of FxPair")

        return fig

    def _get_accounts(self,
                      company: Optional[CompanyTypes] = None,
                      accounts: Optional[Iterable[AccountTypes]] = None):
        # Check that at least one of company or account is provided.
        if company is None and accounts is None:
            raise ValueError("expect either a company or an iterable of accounts")

        # Create list of accounts to plot.
        if accounts and company:
            return [Account.get_account(name=(company.name, account)) if isinstance(account, str)
                    else Account.get_account(account=account) for account in accounts]
        elif accounts:
            return [Account.get_account(account=account) for account in accounts]
        else:
            return Account.get_account_objs(company=company)
