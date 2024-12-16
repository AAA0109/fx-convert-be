import pandas as pd
from scipy.stats import norm

from main.apps.pricing.services.fee.product.base import BasePricing, BaseRecurringCashflowPricing


class ParachutePricing(BasePricing):
    def __init__(
        self,
        annualized_volatility: float,
        settlement_days: int,
        target_eff: float,
        cashflow: float,
        size_category: int,
        safeguard: bool,
        max_loss: float,

    ):
        super().__init__(
            annualized_volatility=annualized_volatility,
            settlement_days=settlement_days,
            target_eff=target_eff,
            cashflow=cashflow,
            size_category=size_category,
        )
        self._safeguard = safeguard
        self._max_loss = max_loss

    @property
    def base_price(self) -> float:
        return 3 * self.std_dev / self._target_eff / 2

    @property
    def risk_reduction(self) -> float:
        return 0.0

    @property
    def upper(self) -> float:
        return 0.0

    @property
    def lower(self) -> float:
        x = self._max_loss / 2 if self._safeguard else self._max_loss
        return (1 - norm.cdf(abs(x), 0, self.std_dev)) * self.base_price * 2


class ParachuteRecurringCashflowPricing(BaseRecurringCashflowPricing):
    def __init__(
        self,
        cashflows: pd.DataFrame,
        target_eff: int,
        size_category: int,

        safeguard: bool,
        max_loss: float,
        estimator_id: int
    ):
        self._cashflows = cashflows
        super().__init__()
        self._pricing_class = ParachutePricing
        self._pricing_config = {
            "target_eff": target_eff,
            "size_category": size_category,
            "safeguard": safeguard,
            "max_loss": max_loss,
        }
        self._estimator_id = estimator_id
