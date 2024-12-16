import glob
import os
import random
import time
from typing import List

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from hdlib.Universe.Universe import Universe

from hdlib.Instrument.CashFlow import CashFlow, CashFlows

from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache

from hdlib.DateTime.DayCounter import DayCounter_HD

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account, AccountTypes
from main.apps.account.services.cashflow_pricer import CashFlowPricerService
from main.apps.currency.models import Currency, FxPair
from main.apps.marketdata.models import FxSpot
from main.apps.marketdata.services.fx.fx_provider import FxVolAndCorrelationProvider, FxSpotProvider
from main.apps.marketdata.services.universe_provider import UniverseProviderService

from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


class StylizedCashflow:
    def __init__(self, currency: Currency, domestic_amount: float, days_till_pay_date: int):
        self._currency = currency
        self._domestic_amount = domestic_amount
        self._days_till_pay_date = days_till_pay_date

        # These are adjusted by stylization
        self.amount = None
        self.pay_date = None

    def restylize(self, date: Date, spot_cache: SpotFxCache, domestic: Currency) -> CashFlow:
        """
        NOTE: Should really re-stylize based on NPV, not current cash amount?
        """
        self.pay_date = date + self._days_till_pay_date
        self.amount = spot_cache.convert_value(from_currency=domestic,
                                               to_currency=self._currency,
                                               value=self._domestic_amount)
        return CashFlow(amount=self.amount, currency=self._currency, pay_date=self.pay_date)


class UniverseCache:
    def __init__(self, fx_pairs, domestic: Currency):
        self.fx_pairs = fx_pairs
        self.domestic = domestic
        self._universe_map = {}

    def get(self,
            ref_date: Date,
            create_vols: bool = True,
            create_corr: bool = True,
            flat_forward: bool = False,
            flat_discount: bool = False,
            ) -> Universe:
        if ref_date in self._universe_map:
            return self._universe_map[ref_date]
        universe = UniverseProviderService().make_cntr_currency_universe(ref_date=ref_date,
                                                                         domestic=self.domestic,
                                                                         fx_pairs=self.fx_pairs,
                                                                         create_vols=create_vols,
                                                                         create_corr=create_corr,
                                                                         flat_forward=flat_forward,
                                                                         flat_discount=flat_discount,
                                                                         bypass_errors=True)
        self._universe_map[ref_date] = universe
        return universe


class UnhedgedBacktester:
    """
    Object that can do a backtest of what the unhedged performance of receiving cashflows would be. This is currently
    much easier to test than a test of what the hedged performance would be since it only requires making some
    universes and spot caches.

    This class also supports loading and saving backtest data sets and functions to process the data.
    """

    def __init__(self, company: str, use_npv: bool = True):
        self._company: Company = Company.get_company(company)
        if not self._company:
            raise Company.NotFound(company)
        self._accounts = list(Account.get_active_accounts(live_only=False, company=self._company))

        self._use_npv = use_npv
        self._print_timing_info = False

        # Data from backtests
        self.num_samples = 0
        self.days_in_backtest = 0
        self.total_values, self.roll_offs, self.npvs = [], [], []
        self.stylization_dates = None
        self.by_date_stats = None

    def set_use_npv(self, use_npv: bool):
        self._use_npv = use_npv

    def stylized_run(self, start_date: Date, end_date: Date, num_samples: int):
        dc = DayCounter_HD()

        # Reset values.
        self.by_date_stats = []

        fx_spot_provider = FxSpotProvider()
        spot_fx_cache = fx_spot_provider.get_spot_cache(time=start_date)
        domestic = self._company.currency

        self.days_in_backtest = dc.days_between(start_date, end_date)

        logger.debug(f"Starting stylized backtest, {self.days_in_backtest} days in time period.")

        # Get the cashflows to run for each account.
        stylized_cashflows_for_accounts, all_fx_pairs = {}, set({})
        horizon = 4 * 365  # NOTE: Get for real.
        cashflows = None
        for account in self._accounts:
            cashflows, fx_pairs, _ = CashFlowPricerService().get_flows_for_account(
                account=account,
                date=start_date,
                max_horizon=self.days_in_backtest + horizon)
            for fx_pair in fx_pairs:
                all_fx_pairs.add(fx_pair)

                # Convert cashflows into constant maturity cashflows.
            stylized_cashflows_for_accounts[account] = []
            for cashflow in cashflows:
                domestic_amount = spot_fx_cache.convert_value(value=cashflow.amount,
                                                              from_currency=cashflow.currency,
                                                              to_currency=domestic)
                days = dc.days_between(start_date, cashflow.pay_date)
                stylized_cashflow = StylizedCashflow(currency=cashflow.currency,
                                                     domestic_amount=domestic_amount,
                                                     days_till_pay_date=days)
                stylized_cashflows_for_accounts[account].append(stylized_cashflow)

        # Nothing to do.
        if cashflows is None:
            return

        # Create universe cache
        ucache = UniverseCache(domestic=domestic, fx_pairs=all_fx_pairs)

        # Get stylization dates.
        min_date, max_date = fx_spot_provider.get_common_date_range(fx_pairs=all_fx_pairs)
        # For now, for safety
        min_date = np.maximum(min_date, Date.create(year=2000, month=1, day=1))

        if dc.days_between(min_date, max_date) < self.days_in_backtest:
            raise ValueError("cannot run")
        num_samples = np.minimum(num_samples, dc.days_between(min_date, max_date) - self.days_in_backtest)
        last_possible_stylization_date = max_date - self.days_in_backtest
        potential_dates = list(Date.yield_range(min_date, last_possible_stylization_date))

        # stylization_dates = sorted(random.sample(stylization_dates, num_samples))
        step = int(len(potential_dates) / num_samples)
        self.stylization_dates = []
        for count in range(num_samples):
            self.stylization_dates.append(potential_dates[count * step])

        # Opening message.
        logger.debug(f"Using {len(self.stylization_dates)} stylized dates.")

        # Compute NPV on the original date.
        universe = ucache.get(ref_date=start_date, create_corr=False, create_vols=False,
                              flat_discount=True, flat_forward=True)
        npv0, _ = CashFlowPricerService().get_npv_for_cashflows(cashflows=cashflows,
                                                                universe=universe,
                                                                domestic=domestic)

        # Reset history.
        self.total_values, self.roll_offs, self.npvs = [], [], []
        self.num_samples = num_samples

        actual_num_samples = 0  # Since some can be thrown away for having NaNs.
        for it, stylization_date in enumerate(self.stylization_dates):
            logger.debug(f"Running on date {it + 1} / {len(self.stylization_dates)} (real date {stylization_date})")
            T1 = time.perf_counter()

            # Timing
            cache_time, universe_time, restylization_time, npv_time, roll_offs_time = 0., 0., 0., 0., 0.

            t1 = time.perf_counter()
            spot_fx_cache = FxSpotProvider().get_spot_cache(time=stylization_date)
            t2 = time.perf_counter()
            cache_time = t2 - t1

            # Stylizes the amounts by keeping the domestic value of each cashflow the same for each stylized
            # starting date.
            t1 = time.perf_counter()
            cashflows_for_accounts = {account: [cashflow.restylize(date=stylization_date,
                                                                   spot_cache=spot_fx_cache,
                                                                   domestic=domestic) for cashflow in cashflows]
                                      for account, cashflows in stylized_cashflows_for_accounts.items()}
            cashflows_for_accounts = {account: CashFlows(cashflows) for account, cashflows
                                      in cashflows_for_accounts.items()}
            t2 = time.perf_counter()
            restylization_time = t2 - t1

            total_value_by_account = {account: [] for account in self._accounts}
            roll_offs_by_account = {account: [0] for account in self._accounts}
            npv_by_account = {account: [] for account in self._accounts}

            last_date = None
            for dt, date in enumerate(Date.yield_range(stylization_date, stylization_date + self.days_in_backtest)):
                # NOTE: Make sure we can construct a universe today, i.e. there is spot FX data.
                t1 = time.perf_counter()
                universe = ucache.get(ref_date=date, create_corr=False, create_vols=False,
                                      flat_discount=True, flat_forward=True)
                t2 = time.perf_counter()
                universe_time += t2 - t1

                for account in self._accounts:
                    cashflows = cashflows_for_accounts[account]

                    # Look for roll off.
                    t1 = time.perf_counter()
                    spot_fx_cache = None
                    roll_off, total_roll_off = 0., 0.
                    if last_date:
                        for cashflow in cashflows:
                            if last_date <= cashflow.pay_date < date:
                                amount = cashflow.amount
                                # Value the cashflow.
                                if not spot_fx_cache:
                                    spot_fx_cache = FxSpotProvider().get_spot_cache(time=date)
                                value = spot_fx_cache.convert_value(value=amount,
                                                                    from_currency=cashflow.currency,
                                                                    to_currency=domestic)
                                roll_off += value

                        roll_off_ts = roll_offs_by_account[account]
                        total_roll_off = roll_off_ts[-1] + roll_off
                        roll_off_ts.append(total_roll_off)
                    t2 = time.perf_counter()
                    roll_off += t2 - t1

                    # Compute future cashflow NPV.
                    t1 = time.perf_counter()
                    if self._use_npv:
                        npv, _ = CashFlowPricerService().get_npv_for_cashflows(cashflows=cashflows,
                                                                               universe=universe,
                                                                               domestic=domestic)
                        # If there was a weekend and a spot could not be found, carry over the last
                        # value (if possible).
                        if np.isnan(npv):
                            if 0 < len(npv_by_account[account]):
                                npv = npv_by_account[account][-1] - roll_off
                            else:
                                npv = npv0

                    else:
                        raise Exception("not implemented option: !use_npv")

                    npv_by_account[account].append(npv)
                    t2 = time.perf_counter()
                    roll_offs_time += t2 - t1

                    # Record the total value.
                    total_value_by_account[account].append(npv + total_roll_off)

                last_date = date

            # Done with a single stylized run. If there wasn't an error (causing the value to be NaN), save.
            all_good = True
            for account in self._accounts:
                if np.isnan(total_value_by_account[account][-1]):
                    all_good = False
            if all_good:
                self.total_values.append(total_value_by_account)
                self.roll_offs.append(roll_offs_by_account)
                self.npvs.append(npv_by_account)
                actual_num_samples += 1
            else:
                logger.warning(f"Could not use the run, NaNs detected.")

            T2 = time.perf_counter()

            # Calculate by-date statistics.
            row = [actual_num_samples, stylization_date]
            for account in self._accounts:
                # Change in value.
                initial_value = total_value_by_account[account][0]
                final_value = total_value_by_account[account][-1]
                row.append(initial_value - final_value)
                # Realized volatility.
                rv, x0 = 0.0, total_value_by_account[account][0]
                for x in total_value_by_account[account][1:]:
                    rv += np.square(x - x0)
                    x0 = x
                vol = np.sqrt(365.25 * rv / self.days_in_backtest)
                row.append(vol)
            self.by_date_stats.append(row)

            # Timing message
            if self._print_timing_info:
                logger.debug(f"Done with run. Timing: "
                            f"\n* Total time: {T2 - T1}"
                            f"\n* Spot cache time: {cache_time}"
                            f"\n* Restylization time: {restylization_time}"
                            f"\n* Universe time: {universe_time}"
                            f"\n* NPV calc time {npv_time}"
                            f"\n* Roll-off calc time: {roll_offs_time}")
        self.num_samples = actual_num_samples

    def get_total_value_trajectory(self, index: int, account: AccountTypes):
        account_ = self._get_account(account)
        return self.total_values[index][account_]

    def total_value_to_frame(self, account: AccountTypes) -> pd.DataFrame:
        account_ = self._get_account(account)
        names, data = [], []
        for it, trajectories in enumerate(self.total_values):
            names.append(f"T_{it}")
            data.append(trajectories[account_])
        return pd.DataFrame(columns=names, data=list(zip(*data)))

    def roll_offs_to_frame(self, account: AccountTypes) -> pd.DataFrame:
        account_ = self._get_account(account)
        names, data = [], []
        for it, trajectories in enumerate(self.roll_offs):
            names.append(f"T_{it}")
            data.append(trajectories[account_])
        return pd.DataFrame(columns=names, data=list(zip(*data)))

    def npvs_to_frame(self, account: AccountTypes) -> pd.DataFrame:
        account_ = self._get_account(account)
        names, data = [], []
        for it, trajectories in enumerate(self.npvs):
            names.append(f"T_{it}")
            data.append(trajectories[account_])
        return pd.DataFrame(columns=names, data=list(zip(*data)))

    def save_metadata_to_directory(self, dirpath: str):
        pd.Series(
            index=["Company", "NumSamples"],
            data=[self._company, self.num_samples],
        ).to_csv(f"{dirpath}/meta.csv", index=False)

    def save_by_date_to_directory(self, dirpath: str):
        header = ["Index", "StylizationDate"]
        for account in self._accounts:
            header.append(f"{account}_ChangeInValue")
            header.append(f"{account}_RealizedVol")
        df = pd.DataFrame(columns=header, data=self.by_date_stats)
        df.to_csv(f"{dirpath}/by-date.csv", index=False)

    def save_simulation_to_directory(self, dirpath: str):
        # Create a directory if necessary.
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)

        self.save_metadata_to_directory(dirpath)
        self.save_by_date_to_directory(dirpath)
        for account in self._accounts:
            self.total_value_to_frame(account=account).to_csv(dirpath + f"/totalvalue_{account.name}.csv")
            self.roll_offs_to_frame(account=account).to_csv(dirpath + f"/rolloff_{account.name}.csv")
            self.npvs_to_frame(account=account).to_csv(dirpath + f"/npv_{account.name}.csv")

    @staticmethod
    def load_simulation_from_directory(dirpath: str) -> 'UnhedgedBacktester':

        # Meta data

        meta = pd.read_csv(f"{dirpath}/meta.csv")  # pd.read_csv(f"{dirpath}/meta.csv")
        company = meta.iloc[0, 0]
        num_samples = int(meta.iloc[1, 0])
        backtester = UnhedgedBacktester(company=company)

        # Dates

        by_date = pd.read_csv(f"{dirpath}/by-date.csv")
        backtester.stylization_dates = by_date["StylizationDate"]

        # Total values

        totalvalue_files = glob.glob(f"{dirpath}/totalvalue_*.csv")
        totalvalue_by_account = {}
        for file in totalvalue_files:
            account_name = UnhedgedBacktester._account_name(file)
            account_ = Account.get_account(name=(company, account_name))
            # backtester._accounts.append(account_)
            totalvalue_by_account[account_] = pd.read_csv(file)

        # Load into backtester.
        backtester.total_values = UnhedgedBacktester._load_from_frame(num_samples, totalvalue_by_account)

        # NPVs

        npv_files = glob.glob(f"{dirpath}/npv_*.csv")
        npv_by_account = {}
        for file in npv_files:
            account_name = UnhedgedBacktester._account_name(file)
            npv_by_account[account_name] = pd.read_csv(file)

        # Load into backtester.
        backtester.npvs = UnhedgedBacktester._load_from_frame(num_samples, npv_by_account)

        # Roll offs

        rolloff_files = glob.glob(f"{dirpath}/rolloff_*.csv")
        rolloff_by_account = {}
        for file in rolloff_files:
            account_name = UnhedgedBacktester._account_name(file)
            rolloff_by_account[account_name] = pd.read_csv(file)

        # Load into backtester.
        backtester.roll_offs = UnhedgedBacktester._load_from_frame(num_samples, rolloff_by_account)

        # Set meta data.
        backtester._company = company
        backtester.num_samples = num_samples

        return backtester

    def create_summary(self, summary_percentiles: List[float] = None) -> pd.Series:
        if summary_percentiles is None:
            summary_percentiles = [0.005, 0.05, 0.1, 0.2, 0.25, 0.5, 0.75, 0.8, 0.9, 0.95, 0.995]
        labels = ["NumSamples"]
        data = [self.num_samples]
        for account in self._accounts:
            percentiles = self.compute_percentiles(
                percentiles=summary_percentiles,
                account=account)
            for perc, ts in zip(summary_percentiles, percentiles):
                labels.append(f"{account}_{perc}_Final")
                labels.append(f"{account}_{perc}_Change")
                data.append(ts[-1])
                data.append(ts[-1] - ts[0])
        return pd.Series(index=labels, data=data)

    @property
    def accounts(self):
        return self._accounts

    def compute_percentiles(self, percentiles: List[float], account: AccountTypes):
        account_ = self._get_account(account)

        if len(self.total_values) == 0 or self.num_samples == 0:
            raise Exception(f"unhedged backtester has no data - perhaps it was not run")
        if self.num_samples == 1:
            raise Exception(f"cannot compute percentiles from a single path")

        cached_calcs = []
        for percentile in percentiles:
            frac = (self.num_samples - 1) * percentile
            lower = int(frac)
            lam = frac - lower

            if lam < 0 or 1 < lam:
                pass

            cached_calcs.append((lower, lam))

        # Precompute

        percentiles = [[] for _ in percentiles]
        for it in range(len(self.total_values[0][account_])):
            values = np.array(sorted([val[account_][it] for val in self.total_values]))

            for jt, (lower, lam) in enumerate(cached_calcs):
                v = values[lower] * (1 - lam) + lam * values[lower + 1]
                percentiles[jt].append(v)

        return percentiles

    def _get_account(self, account: AccountTypes):
        account_ = Account.get_account(account)
        if not account_:
            raise Account.NotFound(account)
        return account_

    @staticmethod
    def _account_name(filename) -> str:
        return "_".join(".".join(filename.split('/')[-1].split('.')[:-1]).split('_')[1:])

    @staticmethod
    def _load_from_frame(num_samples: int, frames_by_account):
        output = []
        for it in range(num_samples):
            values_by_account = {}
            for account, df in frames_by_account.items():
                values_by_account[account] = df[f"T_{it}"].values
            output.append(values_by_account)
        return output
