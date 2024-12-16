import time
import os
from typing import List, Iterable, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from hdlib.Universe.Universe import Universe

from hdlib.DateTime.Date import Date
from hdlib.DateTime.Calendar.Calendar import Calendar
from hdlib.DateTime.Calendar.USCalendar import USCalendar, USCalendarType
from hdlib.Hedge.Fx.HedgeAccount import HedgeMethod
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.history.models import AccountSnapshot, CompanySnapshot
from main.apps.history.services.visualization import SnapshotVisualizationService
from main.apps.util import ActionStatus
from main.apps.account.models import Company
from main.apps.hedge.services.eod_and_intra import EodAndIntraService
from main.apps.oems.services.order_service import OrderService
from main.apps.hedge.models import CompanyHedgeAction
from main.apps.hedge.services.pnl import PnLProviderService
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.account.models.account import Account
from main.apps.history.services.snapshot_provider import SnapshotProvider, SnapshotSummaryStats
from main.apps.hedge.models.hedgesettings import HedgeSettings

from django.db import models

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


class Backtester(object):
    def __init__(self,
                 test_name: str,
                 companies: Iterable[str],
                 base_dir: Optional[str] = None):
        self._test_name = test_name
        self._companies = [Company.get_company(company) for company in companies]
        self._accounts = [account for company in self._companies
                          for account in Account.get_active_accounts(live_only=False, company=company)]

        self._out_dir = None
        self.set_base_dir(base_dir=base_dir)

        # If the OMS is not ready for you to complete EOD, wait this long.
        self._retry_time = 15

        # Holiday calendar
        self.holiday_calendar: Optional[Calendar] = USCalendar(cal_type=USCalendarType.US_SETTLEMENT)
        self._snapshot_provider = SnapshotProvider()

    def set_base_dir(self, base_dir: Optional[str]):
        self._out_dir = f"{base_dir}/{self._test_name}" if base_dir else None

    def set_holiday_calendar(self, calendar: Optional[Calendar]):
        """ Set the holiday calendar. Set the calendar to be None to try to run on every day. """
        self.holiday_calendar = calendar

    def generate_summary_package(self, start_date: Date, end_date: Date):
        # Generate no output if out_dir is set to be None.
        if not self._out_dir:
            return

        os.makedirs(self._out_dir, exist_ok=True)

        logger.debug("Generating Summary Package")
        summaries = []
        for company in self._companies:
            for account in Account.get_active_accounts(live_only=False, company=company):
                settings = HedgeSettings.get_hedge_account_settings_hdl(account=account)
                if settings.method == HedgeMethod.MIN_VAR:
                    target_reduction = settings.custom_settings['VolTargetReduction']
                elif settings.method == HedgeMethod.PERFECT:
                    target_reduction = settings.custom_settings['UniformRatio']
                else:
                    target_reduction = np.nan

                logger.debug(f"Stats for account: {account.name}\n")
                stats = self._snapshot_provider.get_account_summary_stats(account=account,
                                                                          start_date=start_date,
                                                                          end_date=end_date)
                if stats:
                    logger.debug(stats)
                    stats = stats.to_series()
                    stats['target_reduction'] = target_reduction
                    summaries.append(stats)
                else:
                    logger.warning("Could not get stats.")

        if 0 < len(summaries):
            merged = pd.concat(summaries, axis=1)
            merged.to_csv(f"{self._out_dir}/snapshot_summaries.csv", index=True, header=False)
        else:
            logger.warning("No summaries to concatenate")

        self._generate_plots(start_date=start_date, end_date=end_date)

    def output_account_snapshots(self, start_date: Date, end_date: Date):
        os.makedirs(f"{self._out_dir}/account_snapshots/", exist_ok=True)

        for account in self._accounts:
            snapshots = self._snapshot_provider.get_account_snapshots(account=account,
                                                                      start_date=start_date,
                                                                      end_date=end_date)

            field_names = [field.name for field in AccountSnapshot._meta.get_fields()
                           if field.name not in ("next", "last", "next_snapshot", "last_snapshot")]

            rows = []
            for snapshot in snapshots:
                row = []
                for field_name in field_names:
                    row.append(getattr(snapshot, field_name))
                rows.append(row)
            summary = pd.DataFrame(data=rows, columns=field_names)
            summary.to_csv(f"{self._out_dir}/account_snapshots/snapshot_{account}.csv", index=False)

    def output_company_snapshots(self, start_date: Date, end_date: Date):
        os.makedirs(f"{self._out_dir}/company_snapshots/", exist_ok=True)

        for company in self._companies:
            snapshots = self._snapshot_provider.get_company_snapshots(company=company,
                                                                      start_date=start_date,
                                                                      end_date=end_date)

            field_names = [field.name for field in CompanySnapshot._meta.get_fields()
                           if field.name not in ("next", "last", "next_snapshot", "last_snapshot")]

            rows = []
            for snapshot in snapshots:
                row = []
                for field_name in field_names:
                    row.append(getattr(snapshot, field_name))
                rows.append(row)
            summary = pd.DataFrame(data=rows, columns=field_names)
            summary.to_csv(f"{self._out_dir}/company_snapshots/snapshot_{company}.csv", index=False)

    def _generate_plots(self, start_date: Date, end_date: Date):

        plot_dir = f"{self._out_dir}/plots"
        os.makedirs(plot_dir, exist_ok=True)
        plt.close('all')

        # Plot values of all accounts.

        fig = SnapshotVisualizationService().create_accounts_values_figure(accounts=self._accounts,
                                                                           start_date=start_date,
                                                                           end_date=end_date)
        fig.savefig(f"{plot_dir}/account_values.png")
        # plt.show()

        # Plot risk reduction
        fig = SnapshotVisualizationService().create_accounts_risk_reduction_figure(accounts=self._accounts,
                                                                                   start_date=start_date,
                                                                                   end_date=end_date)
        fig.savefig(f"{plot_dir}/risk_reductions.png")

        # Account Allocation
        allocations_dir = f"{plot_dir}/allocations"
        os.makedirs(allocations_dir, exist_ok=True)
        for account in self._accounts:
            fig = SnapshotVisualizationService().create_account_allocation_plot(account=account,
                                                                                start_date=start_date,
                                                                                end_date=end_date)
            fig.savefig(f"{allocations_dir}/allocation_{account.company}_{account.name}.png")

    def run(self, start_date: Date, end_date: Date):
        date = start_date
        it = 1
        while date <= end_date:
            # Optionally skip simulation on non-business days.
            if self.holiday_calendar:
                while self.holiday_calendar.is_holiday(date):
                    date += 1

            if end_date < date:
                break

            logger.debug(f"Starting simulation of day {date} (day {it}).")

            # Initialize the EOD Service
            eod_service = EodAndIntraService(ref_date=date)

            # Run EOD Flow
            for company in self._companies:
                logger.debug(f"Running for Company: {company}")
                try:
                    status = self._run_EOD_flow(date=date, company=company, eod_service=eod_service)
                except Exception as e:
                    # Don't keep simulating if there are errors.
                    logger.error(f"Error on {date} for company {company}: {e}")
                    break

                # Don't keep simulating if there are errors.
                if status.is_error():
                    logger.error(f"Error running EOD flow. Not continuing simulation.")
                    break

            logger.debug(f"Ending simulation of day {date}.\n\n")
            # Go to the next date.
            date += 1
            it += 1

        logger.debug("Done with RUNNING.")
        self.generate_summary_package(start_date=start_date, end_date=end_date)

    def _run_EOD_flow(self,
                      date: Date,
                      eod_service: EodAndIntraService,
                      company: Company) -> ActionStatus:
        start_time = Date.now()
        logger.debug(f"Starting EOD flow for {company} at simulated time {date}")
        status = eod_service.start_eod_flow_for_company(time=date, company=company)
        logger.debug(f"Done starting EOD flow for {company}, status: {status}")
        if not status.is_error():
            logger.debug(f"Ending EOD flow for {company}")

            company_hedge_action = CompanyHedgeAction.get_latest_company_hedge_action(company=company, time=date)
            logger.debug(f"Last company hedge action was id = {company_hedge_action.id}.")

            self._wait_for_OMS_to_complete_orders(company=company)

            # Some time went by waiting for the orders to fill.
            ready_for_end_time = Date.now()
            diff = ready_for_end_time - start_time
            date_end_time = date + diff

            logger.debug(f"Ending EOD flow for {company} at simulated time {date_end_time}")
            status = eod_service.end_eod_flow_for_company(time=date_end_time, company=company)
            logger.debug(f"Ended EOD flow for company. Status was: {status}")

            universe = eod_service.get_universe()

            self._log_pnls(company_hedge_action, date_end_time, universe=universe)

        else:
            logger.error(f"Status was error from starting EOD flow: {status}")

        return status

    def _wait_for_OMS_to_complete_orders(self, company: Company):
        if Account.has_live_accounts(company=company):
            while not OrderService.are_company_orders_done(company=company):
                logger.debug(
                    f"Waiting for OMS to fill orders for {company}. "
                    f"Waiting {self._retry_time} seconds...")
                time.sleep(self._retry_time)
        logger.debug(f"Orders filled for {company}. Ready to continue.")

    def _log_pnls(self, company_hedge_action: CompanyHedgeAction, date_end_time: Date, universe: Universe):
        # Compute PnLs.
        company = company_hedge_action.company
        realized_pnl = PnLProviderService().get_realized_pnl(company=company, spot_fx_cache=universe).total_pnl
        unrealized_pnl = PnLProviderService().get_unrealized_pnl(date=date_end_time, company=company).total_pnl
        logger.debug(f"Realized PnL: {realized_pnl}, Unrealized PnL: {unrealized_pnl}")

    def _print_company_positions(self, date: Date):
        # Company's current positions.
        for company in self._companies:
            company_positions = HedgePositionService().get_positions_for_company_by_account(company=company,
                                                                                            time=date)
            cache = FxSpotProvider().get_eod_spot_fx_cache(date=date)
            print(f"Positions for {company}")
            if len(company_positions) == 0:
                print("\tNO POSITIONS!")
            for account, positions in company_positions.items():
                print(f"\tAccount \"{account.name}\":")
                for position in positions:
                    # if position.amount != 0:
                    print(f"\t\t{position.fxpair}: {position.amount}, "
                          f"Px0 = {np.sign(position.amount) * position.total_price}, "
                          f"PxT = {cache.position_value(position)}, "
                          f"FX = {cache.get_fx(position.fxpair)}")
