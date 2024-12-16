from dataclasses import dataclass
from typing import List, Optional

from main.apps.account.models.company import Company
from main.apps.pricing.services.fee.product.autopilot.formula import AutopilotRecurringCashflowPricing
from main.apps.pricing.services.fee.product.pricing_strategy import StrategyConfig, PricingStrategyInterface, OutputPrice, Cashflow


@dataclass
class AutopilotStrategyConfig(StrategyConfig):
    strategy = 'autopilot'
    risk_reduction: float
    upper_limit: Optional[float] = None
    lower_limit: Optional[float] = None


class AutopilotCalculator(PricingStrategyInterface):

    def get_pricing_for_strategy(self, cashflows: List[Cashflow],
                                 strategy_config: AutopilotStrategyConfig,
                                 size: Company.EstimatedAumType.values) -> OutputPrice:
        """
        Calculate and return the pricing based on the given strategy and its configuration.
        """
        cashflows_df = self._cashflows_to_dataframe(cashflows)
        normalized_cashflows = self._normalize_amount(cashflows_df)
        size_category = self._get_size_category(size)
        target_eff = 30
        estimator_id = 3

        if strategy_config.upper_limit is None or strategy_config.upper_limit == 0.0:
            upside_on = False
        else:
            upside_on = True

        if strategy_config.lower_limit is None or strategy_config.lower_limit == 0.0:
            downside_on = False
        else:
            downside_on = True

        pricing = AutopilotRecurringCashflowPricing(
            cashflows=normalized_cashflows,
            target_eff=target_eff,
            size_category=size_category,
            risk_red=strategy_config.risk_reduction,
            upside_on=upside_on,
            downside_on=downside_on,
            upside=strategy_config.upper_limit,
            downside=strategy_config.lower_limit,
            estimator_id=estimator_id
        )
        return OutputPrice(cost=pricing.cost, bps=pricing.bps, percentage=pricing.percentage)
