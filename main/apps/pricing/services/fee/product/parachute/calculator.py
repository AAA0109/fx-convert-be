from dataclasses import dataclass
from typing import List

from main.apps.account.models.company import Company
from main.apps.pricing.services.fee.product.parachute.formula import ParachuteRecurringCashflowPricing
from main.apps.pricing.services.fee.product.pricing_strategy import StrategyConfig, PricingStrategyInterface, Cashflow, OutputPrice


@dataclass
class ParachuteStrategyConfig(StrategyConfig):
    lower_limit: float
    safeguard: bool


class ParachuteCalculator(PricingStrategyInterface):

    def get_pricing_for_strategy(self, cashflows: List[Cashflow],
                                 strategy_config: ParachuteStrategyConfig,
                                 size: Company.EstimatedAumType.values) -> OutputPrice:
        """
        Calculate and return the pricing based on the given strategy and its configuration.
        """
        cashflows_df = self._cashflows_to_dataframe(cashflows)
        normalized_cashflows = self._normalize_amount(cashflows_df)
        size_category = self._get_size_category(size)
        target_eff = 25
        estimator_id = 3

        pricing = ParachuteRecurringCashflowPricing(
            cashflows=normalized_cashflows,
            target_eff=target_eff,
            size_category=size_category,
            safeguard=strategy_config.safeguard,
            max_loss=strategy_config.lower_limit,
            estimator_id=estimator_id

        )
        return OutputPrice(cost=pricing.cost, bps=pricing.bps, percentage=pricing.percentage)
