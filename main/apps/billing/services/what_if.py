from typing import Optional, Sequence, Iterable

from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.account.models import Account, CashFlow, iter_active_cashflows
from main.apps.account.models.company import Company
from main.apps.billing.calculators.fee_calculator import FeeCalculatorServiceInterface, DefaultFeeCalculatorService

import logging

logger = logging.getLogger(__name__)


class FeeDetail(object):
    def __init__(self,
                 cashflow_total: float,
                 num_cashflows: int,
                 maturity_days: int,
                 new_cashflow_fee: float,
                 aum_total_fee: float,
                 new_cashflow_fee_rate: float,
                 aum_fee_rate: float,
                 previous_rolling_aum: float,
                 previous_daily_aum: float):
        """
        Container of details related to fees for the addition of a set of cashflows (to some account)
        :param cashflow_total: float, sum of absolute cashflows, in units of domestic
        :param num_cashflows: int, total number of RAW cashflows (ie recurring cashflows get expanded into raw)
        :param maturity_days: int, days until maturity of the LAST cashflow in the group
        :param new_cashflow_fee: float, total NEW_CASHFLOW_FEE incurred for the new cashflows
        :param aum_total_fee: float, total AUM_MAINTENANCE_FEE incurred over the life of the cashflows
        :param new_cashflow_fee_rate: float, the rate for cashflows based on current tier
        :param aum_fee_rate: float, the annualized rate for cashflows based on current tier, note that
            this is NOT the rate as a fraction of cashflows
        :param previous_rolling_aum: float, the previous rolling average AUM used in determining the tier
        :param previous_daily_aum: float, the previous daily AUM
        """
        self.cashflow_total = cashflow_total
        self.num_cashflows = num_cashflows
        self.maturity_days = maturity_days

        # Totals
        self.new_cashflow_fee = new_cashflow_fee
        self.aum_total_fee = aum_total_fee

        # Rates
        self.new_cashflow_fee_rate = new_cashflow_fee_rate
        self.aum_fee_rate = aum_fee_rate  # This is annual rate, not rate as fraction of cashflow

        self.previous_rolling_aum = previous_rolling_aum
        self.previous_daily_aum = previous_daily_aum

    @property
    def cost_total(self) -> float:
        return self.new_cashflow_fee + self.aum_total_fee

    @property
    def aum_fee_rate_of_cashflows(self) -> float:
        return self.aum_total_fee / self.cashflow_total if self.cashflow_total != 0 else 0

    @staticmethod
    def new_all_zeros() -> 'FeeDetail':
        return FeeDetail(cashflow_total=0.,
                         num_cashflows=0,
                         maturity_days=0,
                         new_cashflow_fee=0.,
                         new_cashflow_fee_rate=0.,
                         aum_fee_rate=0.,
                         aum_total_fee=0.,
                         previous_rolling_aum=0.,
                         previous_daily_aum=0.)


class FeeWhatIfService(object):
    """
    Service for running the daily AUM fee assessment for customers. This is mainly to provide EOD functionality
    for billing AUM
    """
    dc = DayCounter_HD()  # TODO: update to pass include_end_date = True

    def __init__(self,
                 fee_calculator: FeeCalculatorServiceInterface = DefaultFeeCalculatorService()):
        """
        :param fee_calculator: FeeCalculatorServiceInterface, used to calculate fees
        """
        self._fee_calculator = fee_calculator

    def get_fee_details_what_if_after_new_cashflows(self,
                                                    date: Date,
                                                    company: Company,
                                                    new_cashflows: Iterable[CashFlow],
                                                    spot_fx_cache: SpotFxCache,
                                                    max_days_away: int = 730
                                                    ) -> FeeDetail:
        logger.debug(f"Running fee what-if for company: {company}")
        logger.debug(f"Retrieving fee rates for {company}")
        aum = self._fee_calculator.get_last_aum(company=company, date=date)
        fee_tier = self._fee_calculator.get_fee_tier(company=company, aum=aum)
        aum_fee_rate = fee_tier.aum_fee_rate  # Annualized rate, in decimal
        previous_rolling_aum = aum.rolling_aum if aum else 0.
        previous_daily_aum = aum.daily_aum if aum else 0.
        logger.debug(f'Previous daily aum {previous_daily_aum} and rolling aum {previous_rolling_aum}, '
                    f'fee rate {aum_fee_rate}')

        fee_currency = company.currency  # TODO: convert to USD hardcoded

        aum_total_fee = 0
        new_cashflow_total_fee = 0
        cashflow_total = 0
        last_cashflow_days = 0
        num_cashflows = 0

        logger.debug(f"Calculating fees for cashflows of {company}")
        for cashflow in iter_active_cashflows(cfs=new_cashflows, ref_date=date, max_days_away=max_days_away,
                                              include_cashflows_on_vd=True, include_end=True):
            if cashflow.pay_date < date:
                continue

            num_cashflows += 1

            # ==================
            # New cashflow fee
            # ==================
            try:
                days_to_paydate = self.dc.days_between(start=date, end=cashflow.pay_date)
                last_cashflow_days = max(last_cashflow_days, days_to_paydate)

                fee, amount_dom = self._fee_calculator.calculate_new_cashflow_fee(fee_tier=fee_tier,
                                                                                  fee_currency=fee_currency,
                                                                                  cashflow=cashflow,
                                                                                  spot_fx_cache=spot_fx_cache)
                new_cashflow_total_fee += fee
                cashflow_total += abs(amount_dom)
            except Exception as e:
                raise RuntimeError(f"Error calculating new cashflow fee for {company}: {e}")

            # ==================
            # Aum fee (need to charge daily fee for every day the cashflow is active)
            # ==================
            aum_cashflow_fee = abs(amount_dom) * aum_fee_rate * self.dc.year_fraction_from_days(days_to_paydate)
            aum_total_fee += aum_cashflow_fee

        return FeeDetail(cashflow_total=cashflow_total,
                         num_cashflows=num_cashflows,
                         maturity_days=last_cashflow_days,
                         new_cashflow_fee=new_cashflow_total_fee,
                         aum_total_fee=aum_total_fee,
                         aum_fee_rate=aum_fee_rate,
                         new_cashflow_fee_rate=fee_tier.new_cash_fee_rate,
                         previous_rolling_aum=previous_rolling_aum,
                         previous_daily_aum=previous_daily_aum)
