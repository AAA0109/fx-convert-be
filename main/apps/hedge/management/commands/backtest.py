import logging

from django.core.management.base import BaseCommand
from hdlib.DateTime.Date import Date

from main.apps.currency.models import Currency
from main.apps.hedge.services.hedger import caching_make_cntr_currency_universe
import time
import os
from typing import List, Iterable, Optional

import numpy as np
import pandas as pd

from hdlib.DateTime.Date import Date
from hdlib.DateTime.Calendar.Calendar import Calendar
from hdlib.DateTime.Calendar.USCalendar import USCalendar, USCalendarType
from hdlib.Hedge.Fx.HedgeAccount import HedgeMethod
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.history.models import AccountSnapshot, CompanySnapshot
from main.apps.history.services.visualization import SnapshotVisualizationService
from main.apps.util import ActionStatus
from main.apps.account.models import Company
from main.apps.hedge.services.eod_and_intra import EodAndIntraService, BacktestEodAndIntraService
from main.apps.oems.services.order_service import OrderService
from main.apps.hedge.models import CompanyHedgeAction
from main.apps.hedge.services.pnl import PnLProviderService
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.account.models.account import Account
from main.apps.history.services.snapshot_provider import SnapshotProvider, SnapshotSummaryStats
from main.apps.hedge.models.hedgesettings import HedgeSettings

logger = logging.getLogger("root")


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: The company id")
        parser.add_argument("--start_date", type=str, help="the backtest start date YYYY-MM-DD")
        parser.add_argument("--end_date", type=str, help="the backtest end date YYYY-MM-DD")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command backtest a company."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]
            start_date: Date = Date.from_str(options["start_date"])
            end_date: Date = Date.from_str(options["end_date"])

            company = Company.objects.get(id=company_id)
            logging.info(f"Running backtest "
                         f"for {company} "
                         f"and date range [{start_date}, {end_date}]")
            backtest = BacktestService(company, start_date, end_date)
            backtest.run()
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)


class BacktestService(object):
    def __init__(self, company: Company, start_date: Date, end_date: Date):
        self._company = company
        self._start_date = start_date
        self._end_date = end_date
        self._holiday_calendar = USCalendar(cal_type=USCalendarType.US_SETTLEMENT)

    def run(self):
        date = self._start_date
        it = 1
        while date <= self._end_date:
            # Optionally skip simulation on non-business days.
            if self._holiday_calendar:
                while self._holiday_calendar.is_holiday(date):
                    date += 1

            if self._end_date < date:
                break

            logger.debug(f"Starting simulation of day {date} (day {it}).")

            # Initialize the EOD Service
            eod_service = BacktestEodAndIntraService(ref_date=date)

            # Run EOD Flow

            logger.debug(f"Running for Company: {self._company}")
            try:
                status = self._run_EOD_flow(date=date, company=self._company, eod_service=eod_service)
            except Exception as e:
                # Don't keep simulating if there are errors.
                logger.error(f"Error on {date} for company {self._company}: {e}")
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

            self._wait_for_OMS_to_complete_orders(hedge_action=company_hedge_action, eod_service=eod_service)

            # Some time went by waiting for the orders to fill.
            ready_for_end_time = Date.now()
            diff = ready_for_end_time - start_time
            date_end_time = date + diff

            logger.debug(f"Ending EOD flow for {company} at simulated time {date_end_time}")
            status = eod_service.end_eod_flow_for_company(time=date_end_time, company=company)
            logger.debug(f"Ended EOD flow for company. Status was: {status}")


        else:
            logger.error(f"Status was error from starting EOD flow: {status}")

        return status

    def _wait_for_OMS_to_complete_orders(self, hedge_action: CompanyHedgeAction, eod_service: EodAndIntraService):
        company = hedge_action.company
        if Account.has_live_accounts(company=hedge_action.company):

            while not eod_service._oms_hedge_service. \
                are_tickets_from_hedge_complete(company_hedge_action=hedge_action,
                                                account_type=Account.AccountType.LIVE):
                logger.debug(
                    f"Waiting for OMS to fill orders for {company}. "
                    f"Waiting {self._retry_time} seconds...")
                time.sleep(self._retry_time)
        logger.debug(f"Orders filled for {company}. Ready to continue.")
