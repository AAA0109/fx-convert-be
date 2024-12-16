from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.Instrument.CashFlow import CashFlows

from main.apps.account.models import Account, CashFlow, iter_active_cashflows, Currency
from main.apps.account.models.company import Company
from main.apps.account.services.cashflow_provider import CashFlowProviderService
from main.apps.billing.support.rolling_aum import RollingAum
from main.apps.billing.models import FeeTier
from main.apps.billing.models.aum import Aum
from main.apps.hedge.models import HedgeSettings
from main.apps.util import get_or_none

from abc import ABC, abstractmethod

from typing import List, Union, Optional, Sequence, Tuple, Iterable, Dict

import logging

logger = logging.getLogger(__name__)


class FeeCalculatorServiceInterface(ABC):
    def __init__(self, dc=DayCounter_HD()):
        self.dc = dc

    @abstractmethod
    def get_fee_tier(self, company: Company, aum: Optional[Aum]) -> FeeTier:
        raise NotImplementedError

    # =======================
    # New Cachflow Related
    # =======================

    def calculate_new_cashflow_fee(self,
                                   fee_tier: FeeTier,
                                   fee_currency: Currency,
                                   cashflow: CashFlow,
                                   spot_fx_cache: SpotFxCache) -> Tuple[float, float]:

        cash_value = spot_fx_cache.convert_value(value=cashflow.amount,
                                                 from_currency=cashflow.currency,
                                                 to_currency=fee_currency)

        fee = fee_tier.new_cash_fee_rate * abs(cash_value)
        return fee, cash_value

    def calculate_new_cashflows_fee(self,
                                    date: Date,
                                    company: Company,
                                    new_cashflows: Iterable[CashFlow],
                                    spot_fx_cache: SpotFxCache,
                                    max_days_away: int = 730) -> Tuple[float, float, int]:
        """ returns [fee, cashflow_total_amount, last_cashflow_date]"""
        aum = self.get_last_aum(company=company, date=date)
        fee_tier = self.get_fee_tier(company=company, aum=aum)
        fee_currency = company.currency  # TODO: convert to USD hardcoded

        total_fee = 0
        total_cash = 0
        last_cashflow_days = 0
        for cashflow in iter_active_cashflows(cfs=new_cashflows, ref_date=date, max_days_away=max_days_away,
                                              include_cashflows_on_vd=True, include_end=True):
            fee, cash_domestic = self.calculate_new_cashflow_fee(fee_tier=fee_tier, fee_currency=fee_currency,
                                                                 cashflow=cashflow, spot_fx_cache=spot_fx_cache)
            total_cash += abs(cash_domestic)
            total_fee += fee
            last_cashflow_days = max(last_cashflow_days, self.dc.days_between(start=date, end=cashflow.pay_date))

        return total_fee, total_cash, last_cashflow_days

    # =======================
    # Aum Related
    # =======================

    @abstractmethod
    def calculate_aum_day_charge(self, date: Date, company: Company, aum: Aum) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_aum_fee_due_date(self, date: Date, company: Company) -> Date:
        raise NotImplementedError

    @abstractmethod
    def calculate_daily_aum(self, company: Company, date: Date, spot_fx_cache: SpotFxCache) -> float:
        raise NotImplementedError

    @abstractmethod
    def calculate_rolling_aum(self, company: Company, date: Date, today_aum: float) -> RollingAum:
        raise NotImplementedError

    @abstractmethod
    @get_or_none
    def get_last_aum(self,
                     company: Company,
                     date: Date) -> Optional[Aum]:
        raise NotImplementedError


class DefaultFeeCalculatorService(FeeCalculatorServiceInterface):
    def __init__(self, dc=DayCounter_HD()):
        super(DefaultFeeCalculatorService, self).__init__(dc=dc)

    def get_fee_tier(self, company: Company, aum: Optional[Aum]) -> FeeTier:
        # Note: we take the maximum of rolling and daily AUM to determine the tier. This ensures that
        #       customers who increase their volume will immediately start getting a better AUM rate. It also
        #       adds a weird consideration for new cashflow fees, that they may be better off splitting up the
        #       addition of new casfhlows by 1 day, in case some cashflows bump them into the next tier, which
        #       they will get on all new casfhlows starting the NEXT day
        aum_level = max(aum.rolling_aum, aum.daily_aum) if aum else 0.
        return FeeTier.get_tier_for_aum_level(company=company,
                                              aum_level=aum_level)

    # =======================
    # Aum Related
    # =======================

    def calculate_aum_day_charge(self, date: Date, company: Company, aum: Aum) -> float:
        # Figure out the fee tier for this payment based on current aum_level
        tier = self.get_fee_tier(company=company, aum=aum)
        annual_rate = tier.aum_fee_rate

        # Determine the daily charge
        one_day_fraction = self.dc.year_fraction_from_days(1)
        day_charge = annual_rate * one_day_fraction * aum.daily_aum
        return day_charge

    def get_aum_fee_due_date(self, date: Date, company: Company) -> Date:
        # TODO: the right thing?
        # TODO: does it matter if we make it due beggining of the day when we are on last day of month?
        due_date = date.last_day_of_month()
        return due_date

    def calculate_daily_aum(self, company: Company, date: Date, spot_fx_cache: SpotFxCache) -> float:
        # 1) Get all live settings for company
        # Make all Hedge Settings
        all_account_settings = list(
            HedgeSettings.get_all_accounts_to_hedge(
                account_types=(Account.AccountType.LIVE,),
                company=company,
                include_no_hedge=True
            ))
        logger.debug(f"Calculating daily AUM from {len(all_account_settings)} live accounts")

        domestic = company.currency  # TODO: convert to USD hardcoded

        # 2) Calc AUM for each account and aggregate
        company_aum = 0

        if len(all_account_settings) == 0:
            return 0

        num_cashflows = 0
        for settings in all_account_settings:
            max_horizon = min(settings.max_horizon_days, 5 * 365)
            cashflows = CashFlowProviderService().get_active_cashflows(start_date=date,
                                                                       account=settings.account, inclusive=True,
                                                                       max_days_away=max_horizon,
                                                                       skip_less_than_ref_date=True)
            cashflows = CashFlows(list(cashflows))
            num_cashflows += len(cashflows)

            _, account_aum = spot_fx_cache.sum_cashflow_spot_values(cashflows=cashflows, currency=domestic)
            logger.debug(f"Account {settings.account.name} contributed {account_aum} "
                        f"to AUM from {len(cashflows)} cashflows")

            company_aum += account_aum

        logger.debug(f"Daily AUM of {company_aum} calculated from {num_cashflows} total cashflows")
        return company_aum

    def calculate_rolling_aum(self, company: Company, date: Date, today_aum: float) -> RollingAum:
        lookback = 364
        lookback_date = Date.to_date(date) - lookback
        aums = self._get_aums(company=company, start_date=lookback_date, end_date=date)
        num_aums = len(aums) + 1  # Plus one b/c we include today's value

        sum_aums = today_aum

        for aum in aums:
            sum_aums += aum.daily_aum

        return RollingAum(todays_aum=today_aum, rolling_aum=sum_aums / num_aums,
                          actual_days_in_window=num_aums, window_size=lookback + 1)

    @get_or_none
    def get_last_aum(self,
                     company: Company,
                     date: Date) -> Optional[Aum]:
        filters = {'company': company,
                   'date__lt': date}

        return Aum.objects.filter(**filters).order_by("-date").first()

    def _get_aums(self,
                  company: Company,
                  start_date: Date,
                  end_date: Date) -> Sequence[Aum]:
        start = start_date.start_of_day()
        end = end_date.start_of_next_day()

        filters = {'company': company,
                   'date__lt': end,
                   'date__gte': start}

        aums = Aum.objects.filter(**filters)
        return aums
