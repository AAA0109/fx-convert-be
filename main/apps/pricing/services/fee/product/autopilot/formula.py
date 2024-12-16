import pandas as pd
from scipy.stats import norm

from main.apps.pricing.services.fee.product.base import BasePricing, BaseRecurringCashflowPricing


class AutopilotPricing(BasePricing):
    def __init__(
        self,
        annualized_volatility: float,
        settlement_days: int,
        target_eff: float,
        cashflow: float,
        size_category: int,
        risk_red: float,
        upside_on: bool,
        downside_on: bool,
        upside: float,
        downside: float,

    ):
        super().__init__(
            annualized_volatility=annualized_volatility,
            settlement_days=settlement_days,
            target_eff=target_eff,
            cashflow=cashflow,
            size_category=size_category,
        )
        self._risk_red = risk_red
        self._upside_on = upside_on
        self._downside_on = downside_on
        self._upside = upside
        self._downside = downside

    @property
    def base_price(self) -> float:
        return 3 * self.std_dev / self._target_eff

    @property
    def risk_reduction(self) -> float:
        return -(1 - self._risk_red)

    @property
    def upper(self) -> float:
        return self._calculate_adjusted_price(abs(self._upside)) if self._upside_on else 0.0

    @property
    def lower(self) -> float:
        return self._calculate_adjusted_price(abs(self._downside)) if self._downside_on else 0.0

    # ================ Private methods ================
    def _calculate_adjusted_price(self, factor) -> float:
        if self._risk_red >= 1:
            cdf_value = 1.0
        else:
            risk_factor = 1 / (1 - self._risk_red)
            cdf_value = norm.cdf(risk_factor * factor, 0, self.std_dev)
        return (1 - self._risk_red) * (1 - cdf_value) * self.base_price


class AutopilotRecurringCashflowPricing(BaseRecurringCashflowPricing):
    def __init__(
        self,
        cashflows: pd.DataFrame,
        target_eff: int,
        size_category: int,

        risk_red: float,
        upside_on: bool,
        downside_on: bool,
        upside: float,
        downside: float,
        estimator_id: int
    ):
        self._cashflows = cashflows
        super().__init__()
        self._pricing_class = AutopilotPricing
        self._pricing_config = {
            "target_eff": target_eff,
            "size_category": size_category,
            "risk_red": risk_red,
            "upside_on": upside_on,
            "downside_on": downside_on,
            "upside": upside,
            "downside": downside,
        }
        self._estimator_id = estimator_id

    @property
    def cost(self) -> float:
        cost = super().cost
        if self._cashflows.shape[0] <= 1:
            return 0.0
        return cost
