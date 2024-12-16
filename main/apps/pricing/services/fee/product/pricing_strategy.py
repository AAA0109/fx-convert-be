from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

import pandas as pd
from hdlib.DateTime.Date import Date

from main.apps.account.models.company import Company
from main.apps.currency.models import Currency
from main.apps.marketdata.models import FxSpotVol
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider


@dataclass
class Cashflow:
    value_date: Date
    from_currency: str
    to_currency: str
    from_amount: float


@dataclass
class StrategyConfig:
    strategy: str


@dataclass
class OutputPrice:
    cost: float
    bps: float
    percentage: float


class PricingStrategyInterface(ABC):

    @abstractmethod
    def get_pricing_for_strategy(self, cashflows: List[Cashflow],
                                 strategy_config: StrategyConfig,
                                 size: Company.EstimatedAumType.values) -> OutputPrice:
        """
        Calculate and return the pricing based on the given strategy and its configuration.
        """
        raise NotImplementedError("get_pricing_for_strategy has not been implemented")

    # ================ Private methods ================

    @staticmethod
    def _cashflows_to_dataframe(cashflows: List[Cashflow]) -> pd.DataFrame:
        data = []
        for cashflow in cashflows:
            data.append({
                'value_date': cashflow.value_date,
                'from_currency': cashflow.from_currency,
                'to_currency': cashflow.to_currency,
                'from_amount': cashflow.from_amount,
            })
        return pd.DataFrame(data)

    @staticmethod
    def _normalize_amount(df: pd.DataFrame) -> pd.DataFrame:
        df_converted = df.copy()
        fx_spot_provider = FxSpotProvider()
        for index, row in df_converted.iterrows():
            normalized_amount = fx_spot_provider.convert_currency_rate(
                from_currency=Currency.get_currency(row['from_currency']),
                to_currency=Currency.get_currency(row['to_currency']),
                amount=row['from_amount']
            )
            df_converted.at[index, 'amount'] = normalized_amount
        return df_converted

    @staticmethod
    def _get_size_category(size: Company.EstimatedAumType.values) -> int:
        if size == Company.EstimatedAumType.AUM_UNDER_10M:
            return 1
        elif size == Company.EstimatedAumType.AUM_10M_TO_100M:
            return 2
        elif size == Company.EstimatedAumType.AUM_100M_TO_1B:
            return 3
        elif size == Company.EstimatedAumType.AUM_ABOVE_1B:
            return 4
        else:
            # Default to lowest tier if None
            return 1
