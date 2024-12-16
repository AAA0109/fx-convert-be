from datetime import datetime

import numpy as np
import pandas as pd
from hdlib.DateTime.Date import Date
from scipy.stats import norm

from main.apps.marketdata.models import FxSpotVol


class BasePricing(object):
    def __init__(
        self,
        annualized_volatility: float,
        settlement_days: float,
        target_eff: float,
        cashflow: float,
        size_category: int
    ):
        self._annualized_volatility = annualized_volatility
        self._settlement_days = settlement_days
        self._target_eff = target_eff
        self._cash_flow = cashflow
        self._size_category = size_category

        self._discount_table = pd.DataFrame({
            'Discount': [1, 2, 3, 4],
            'Client Size in annual volume': ['<10M', '<100M', '<1B', '>=1B'],
            'Size Factor (SF)': [1.00, 0.80, 0.60, 0.30]
        })

    def sigma(self, pnl) -> float:
        return pnl / self.std_dev

    def probability(self, pnl) -> float:
        return 1 - norm.cdf(pnl, 0, self.std_dev)

    @property
    def std_dev(self) -> float:
        return self._annualized_volatility / np.sqrt(365 / self._settlement_days)

    @property
    def size_of_client(self) -> float:
        discount_row = self._discount_table.loc[self._discount_table['Discount'] == self._size_category]
        size_factor = discount_row['Size Factor (SF)'].values[0]
        size_of_client = -(1 - size_factor)
        return size_of_client

    @property
    def subtotal(self) -> float:
        return self.base_price * (1 + self.risk_reduction) * (1 + self.size_of_client)

    @property
    def total_cost(self) -> float:
        return self.subtotal + self.upper + self.lower

    @property
    def cost(self) -> float:
        return self._cash_flow * self.total_cost

    @property
    def base_price(self) -> float:
        raise NotImplementedError

    @property
    def risk_reduction(self) -> float:
        raise NotImplementedError

    @property
    def upper(self) -> float:
        raise NotImplementedError

    @property
    def lower(self) -> float:
        raise NotImplementedError


class BaseRecurringCashflowPricing(object):
    _pricing_class: type[BasePricing]
    _pricing_config: dict
    _cashflows: pd.DataFrame
    _estimator_id: int

    def __init__(self):
        self._validate_cashflows(self._cashflows)
        self._cashflows = self._calculate_days(self._cashflows)

    @property
    def cost(self) -> float:
        total_cost = 0.0
        for idx, row in self._cashflows.iterrows():
            self._pricing_config["cashflow"] = abs(row["amount"])
            self._pricing_config["settlement_days"] = row["days"]
            self._pricing_config["annualized_volatility"] = self._get_volatility(row["from_currency"],
                                                                                 row["to_currency"],
                                                                                 self._estimator_id)
            pricing_method = self._pricing_class(**self._pricing_config)
            total_cost = total_cost + pricing_method.cost
        return total_cost

    @property
    def percentage(self) -> float:
        return (self.cost / self.total_amount) * 100

    @property
    def bps(self) -> float:
        return self.percentage * 100

    @property
    def total_amount(self) -> float:
        return self._cashflows['amount'].abs().sum()

    # ================ Private methods ================
    @staticmethod
    def _validate_cashflows(dataframe: pd.DataFrame):
        errors = []

        # Check for 'value_date' column existence
        if 'value_date' not in dataframe.columns:
            errors.append("Column 'value_date' is missing.")

        # Check for 'from_currency' column existence
        if 'from_currency' not in dataframe.columns:
            errors.append("Column 'from_currency' is missing.")

            # Check for 'to_currency' column existence
        if 'to_currency' not in dataframe.columns:
            errors.append("Column 'to_currency' is missing.")

        # Check for 'from_amount' column existence
        if 'from_amount' not in dataframe.columns:
            errors.append("Column 'from_amount' is missing.")

        # Check if 'value_date' are datetime
        if not all(isinstance(x, datetime) for x in dataframe['value_date']):
            errors.append("Not all values in 'value_date' are datetime.")

        # Check if 'from_amount' are numbers
        if not all(isinstance(x, (int, float)) for x in dataframe['from_amount']):
            errors.append("Not all values in 'from_amount' are numbers.")

        if errors:
            raise ValueError("Validation errors: " + "; ".join(errors))

    @staticmethod
    def _calculate_days(cashflows: pd.DataFrame) -> pd.DataFrame:
        cashflows['value_date'] = pd.to_datetime(cashflows['value_date'])
        # date has to be in UTC
        base_date = Date.today()
        cashflows['days'] = (cashflows['value_date'] - base_date).dt.days
        return cashflows

    @staticmethod
    def _get_volatility(from_currency: str, to_currency: str, estimator_id: int) -> float:
        pair = f"{from_currency}/{to_currency}"
        fxspotvol = FxSpotVol.get_spot_vol(pair, estimator=estimator_id, date=Date.today())
        if fxspotvol is None:
            raise ValueError(f"No spot volatility found for {pair}")
        return fxspotvol[0]
