import os
import string
import sys
import random
from typing import Iterable, Optional, Tuple, Union, Dict, Sequence

import numpy as np

from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Calendar.Calendar import Calendar
from hdlib.DateTime.Calendar.USCalendar import USCalendar, USCalendarType
from hdlib.DateTime.Date import Date
from hdlib.Instrument.CashFlow import CashFlow as CashFlowHDL
from hdlib.Instrument.RecurringCashFlowGenerator import RecurringCashFlow as RecurringCashFlowHDL

from main.apps.account.models import Company, CashFlow, Account, BrokerAccount, Broker
from main.apps.currency.models import CurrencyTypes, Currency
from main.apps.hedge.models import HedgeSettings
from main.apps.hedge.services.account_manager import AccountManagerService
from main.apps.history.services.snapshot import SnapshotProvider
from scripts.backtest.utils.Backtester import Backtester

logger = get_logger(level=logging.INFO)

CompanyName = str
AccountName = str


class CompanyScenario:
    def __init__(self, start_date: Date):
        # Create a random tag with which we can mangle names.
        self._random_tag = ''.join(random.choices(string.ascii_lowercase, k=10))

        # Map from user names for companies to the actual company object.
        self._companies = {}
        # Map from company name to account name to account.
        self._accounts = {}

        self._backtester = None
        self._holiday_calendar: Optional[Calendar] = USCalendar(cal_type=USCalendarType.US_SETTLEMENT)

        # The initial date. This should not be changed.
        self._start_date = start_date

        # Current date is the next date to be hedged.
        self._current_date = start_date

        # Providers / Services
        self._snapshot_provider = SnapshotProvider()
        self._account_manager = AccountManagerService()

    # ===============================================================
    #  Set up functions.
    # ===============================================================

    def create_company(self, company_name: str, currency: CurrencyTypes, add_tag: bool = True):
        name = f"{self._random_tag}:CS:{company_name}" if add_tag else company_name
        company = Company.create_company(name=name, currency=currency)
        self._companies[company_name] = company
        self._accounts[company_name] = {}

    def create_account(self, company_name: str, account_name: str):
        name = f"{self._random_tag}:CS:{account_name}"
        account = self._account_manager.create_account(
            name=name,
            company=self._get_company(company_name),
            account_type=Account.AccountType.DEMO)
        # Record the account.
        self._accounts[company_name][account_name] = account

    def add_cashflow_to_account(self,
                                name: Tuple[CompanyName, AccountName],
                                cashflow: Union[CashFlowHDL, RecurringCashFlowHDL]):
        self._account_manager.add_cashflow_to_account(account=self._get_account(name), cashflow=cashflow)

    def set_backtest_holiday_calendar(self, calendar: Optional[Calendar]):
        self._holiday_calendar = calendar

    def set_hedge_settings(self,
                           name: Tuple[CompanyName, AccountName],
                           margin_budget: float = np.inf,
                           method: str = "MIN_VAR",
                           max_horizon_days: int = 365 * 20,
                           custom=None):
        HedgeSettings.create_or_update_settings(account=self._get_account(name),
                                                margin_budget=margin_budget,
                                                method=method,
                                                max_horizon_days=max_horizon_days,
                                                custom=custom)

    def set_company_broker_account(self,
                                   company_name: CompanyName,
                                   broker_account_name: str,
                                   is_live: bool = False,
                                   broker_name: str = "IBKR"):
        company = self._get_company(company_name=company_name)
        account_type = BrokerAccount.AccountType.LIVE if is_live else BrokerAccount.AccountType.PAPER
        broker_ = Broker.get_broker(broker_name)
        BrokerAccount.create_account_for_company(company=company,
                                                 broker=broker_,
                                                 broker_account_name=broker_account_name,
                                                 account_type=account_type)

    # ===============================================================
    #  Advancement functions.
    # ===============================================================

    def advance_to_first_business_date(self):
        """
        Advance the backtester so the next day to run is a business day. If the current day is a business day, or the
        calendar is None, the date does not advance.
        """
        if self._holiday_calendar:
            while self._holiday_calendar.is_holiday(self._current_date):
                self._current_date += 1

    def run_backtest_until(self, end_date: Date):
        if end_date < self._current_date:
            return

        # Get the list of companies (with potentially mangled name).
        bt_companies = self._companies.values()

        self._backtester = Backtester(test_name=self._random_tag, companies=bt_companies)
        self._backtester.set_holiday_calendar(self._holiday_calendar)

        self._backtester.run(start_date=self._current_date,
                             end_date=end_date)
        # The next date that has yet to be hedged is the day after the last day that we hedged.
        self._current_date = end_date + 1

    # ===============================================================
    #  Accessors
    # ===============================================================

    def get_current_date(self):
        return self._current_date

    def get_cashflows_by_currency(self,
                                  company_name: Optional[CompanyName] = None,
                                  name: Optional[Tuple[CompanyName, AccountName]] = None
                                  ) -> Dict[Currency, Sequence[CashFlow]]:
        if company_name is not None and name is not None:
            raise ValueError("either specify company or (company, account), not both")
        if company_name is None and name is None:
            raise ValueError("need to specify either company or (company, account)")

        if company_name:
            company = self._get_company(company_name=company_name)
            all_accounts = self._account_manager.get_all_accounts_for_company(company)
        else:
            all_accounts = [self._get_account(name_pair=name)]

        cashflows = {}
        for account in all_accounts:
            cfs = CashFlow.get_active_cashflows(start_date=self._current_date, account=account)
            for cf in cfs:
                if cf.currency not in cashflows:
                    cashflows[cf.currency] = []
                cashflows[cf.currency].append(cf)

        return cashflows

    def get_dates_run(self) -> Optional[Tuple[Date, Date]]:
        """
        Return the first and last date for which the backtester has run. If no days have been run, returns None.
        """
        d = self._current_date - 1
        if self._start_date <= d:
            return self._start_date, d
        return None

    def get_current_cashflow_rolled_off(self):
        """
        Get the current value of cashflow rolloffs from the most recent company snapshot.
        """

    def get_account_snapshots(self,
                              name: Tuple[CompanyName, AccountName],
                              start_date: Optional[Date] = None,
                              end_date: Optional[Date] = None):
        """
        Get the account snapshots for an account during a period of time.
        """
        account = self._get_account(name_pair=name)
        start_date, end_date = self._clip_date_range(start_date, end_date)
        if not start_date:
            return []
        return self._snapshot_provider.get_account_snapshots(account,
                                                             start_date=start_date,
                                                             end_date=end_date)

    def get_company_snapshots(self,
                              name: CompanyName,
                              start_date: Optional[Date] = None,
                              end_date: Optional[Date] = None):
        company = self._get_company(company_name=name)
        start_date, end_date = self._clip_date_range(start_date, end_date)
        if not start_date:
            return []
        return self._snapshot_provider.get_company_snapshots(company=company,
                                                             start_date=start_date,
                                                             end_date=end_date)

    # ===============================================================
    #  Cleaning functions.
    # ===============================================================

    def full_clean_up(self):
        for _, company in self._companies.items():
            company.delete()

    @staticmethod
    def clean_old_companies_from_scenarios():
        """
        Go through the companies and look for any that appear to have been generated by a CompanyScenario.
        This allows cleaning up the database in case full_clean_up was not called in some test, or a test crashed
        before clean up could be called.
        """
        Company.objects.filter(name__contains=":CS:").delete()

    # ===============================================================
    #  Private helper functions.
    # ===============================================================

    def _get_company(self, company_name: CompanyName) -> Company:
        return self._companies[company_name]

    def _get_account(self, name_pair: Tuple[CompanyName, AccountName]):
        return self._accounts[name_pair[0]][name_pair[1]]

    def _clip_date_range(self,
                         start_date: Optional[Date],
                         end_date: Optional[Date]) -> Tuple[Optional[Date], Optional[Date]]:
        if self._current_date == self._start_date:
            return None, None
        start_date = max(start_date, self._start_date) if start_date else self._start_date
        end_date = min(end_date, self._current_date - 1) if end_date else self._current_date - 1
        return start_date, end_date
