from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.Core.FxPair import FxPair as FxPairHDL

from main.apps.account.models import Account, CashFlow, iter_active_cashflows
from main.apps.account.models.company import Company
from main.apps.hedge.calculators.cost import RollCostCalculator, StandardRollCostCalculator
from main.apps.hedge.services.cost import CostProviderService, RatesCache

from typing import Optional, Sequence, Iterable
import logging

logger = logging.getLogger(__name__)


class RollCostDetail(object):
    def __init__(self,
                 cost_total: float,
                 cashflow_total: float,
                 num_cashflows: int):
        self.cost_total = cost_total
        self.cashflow_total = cashflow_total
        self.num_cashflows = num_cashflows

    @property
    def roll_cost_proportion_of_cashflows(self) -> float:
        return self.cost_total / self.cashflow_total if self.cashflow_total > 0 else 0.

    @staticmethod
    def new_all_zeros() -> 'RollCostDetail':
        return RollCostDetail(cost_total=0, cashflow_total=0., num_cashflows=0)


class RollCostWhatIfService(object):
    """
    Service for running the daily AUM fee assessment for customers. This is mainly to provide EOD functionality
    for billing AUM
    """
    dc = DayCounter_HD()  # TODO: update to pass include_end_date = True

    def __init__(self,
                 cost_calculator: RollCostCalculator = StandardRollCostCalculator(),
                 cost_provider: CostProviderService = CostProviderService()):
        """
        :param cost_calculator: CostCalculator, used to estiamte roll costs
        """
        self._cost_calculator = cost_calculator
        self._cost_provider = cost_provider

    def get_roll_cost_estimate_what_if_after_trades(self,
                                                    date: Date,
                                                    company: Company,
                                                    new_cashflows: Iterable[CashFlow],
                                                    spot_fx_cache: SpotFxCache,
                                                    rates_cache: Optional[RatesCache] = None,
                                                    max_days_away: int = 730
                                                    ) -> RollCostDetail:
        # NOTE: we return postive is a COST, negative is a GAIN (this is the opposite convention as usual
        logger.debug(f"Running roll cost what-if for company: {company}")

        domestic_currency = company.currency

        cashflow_total = 0
        last_cashflow_days = 0
        roll_cost_total = 0
        num_cashflows = 0

        # TODO: actually supply the broker
        try:
            rates_cache = rates_cache if rates_cache is not None \
                else self._cost_provider.create_rates_cache(time=date)
        except Exception as e:
            raise RuntimeError(f"Error getting rates cache for roll cost what if: {e}")

        logger.debug(f"Calculating project roll costs for cashflows of {company}")
        for cashflow in iter_active_cashflows(cfs=new_cashflows, ref_date=date, max_days_away=max_days_away,
                                              include_cashflows_on_vd=True, include_end=True):
            if cashflow.pay_date < date:
                continue

            if cashflow.currency == domestic_currency:
                continue

            num_cashflows += 1

            try:
                days_to_paydate = self.dc.days_between(start=date, end=cashflow.pay_date)
                last_cashflow_days = max(last_cashflow_days, days_to_paydate)

                fx_pair = FxPairHDL(base=cashflow.currency, quote=domestic_currency)
                fx_rate = spot_fx_cache.get_fx(fx_pair=fx_pair)
                if fx_rate is None:
                    raise RuntimeError(f'Unable to get Fx rate for pair: {fx_pair}')

                cashflow_total += fx_rate * abs(cashflow.amount)

                # ==================
                # Roll Charge
                # ==================

                # NOTE: we assume a 100% hedge for this calc. If you are hedging say 50%, just multiply the final
                # cost by 50% to get a reasonable estimate for the future roll cost
                hedge_amount = -cashflow.amount

                roll_cost = self._cost_calculator.get_roll_cost_for_fx_position(start_date=date,
                                                                                end_date=cashflow.pay_date,
                                                                                dc=self.dc,
                                                                                fx_pair=fx_pair,
                                                                                fx_spot=fx_rate,
                                                                                rates_cache=rates_cache,
                                                                                amount=hedge_amount)
                roll_cost_total += roll_cost

            except Exception as e:
                raise RuntimeError(f"Error calculating what if roll cost for {company}: {e}")

        # NOTE: we negate it, so POSITIVE represents a COST
        roll_cost_total = -roll_cost_total
        logger.debug(f"Done calculating what if roll costs of {roll_cost_total} for company {company},"
                    f" with {num_cashflows} cashflows totaling {cashflow_total}")

        return RollCostDetail(cashflow_total=cashflow_total, cost_total=roll_cost_total, num_cashflows=num_cashflows)
