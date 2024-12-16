from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache
from hdlib.DataProvider.Fx.FxSpotVols import FxSpotVols
from hdlib.Core.Currency import CustomCurrency

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from scipy.stats import norm

from main.apps.currency.models import Currency

import logging

logger = logging.getLogger(__name__)


class MarginCalculator(ABC):
    @abstractmethod
    def compute_margin_for_position(self,
                                    positions: pd.Series,
                                    domestic: Currency) -> float:
        raise NotImplementedError


class MarginCalculator_NoMargin(MarginCalculator):
    def compute_margin_for_position(self,
                                    positions: pd.Series,
                                    domestic: Currency) -> float:
        return 0


class MarginCalculator_UnivariateGaussian(MarginCalculator):
    def __init__(self,
                 spot_vols: FxSpotVols,
                 spot_fx_cache: SpotFxCache,
                 var_level: float = 0.99,
                 holding_period: float = 5. / 252):
        """"""
        self._spot_fx_cache = spot_fx_cache
        self._var_level = var_level
        self._spot_vols = spot_vols
        self._hp = holding_period
        self._sqrt_hp = np.sqrt(holding_period)

    def compute_margin_for_position(self,
                                    positions: pd.Series,
                                    domestic: Currency) -> float:
        margin = 0
        for fx_pair, value in positions.items():
            margin += self._calc_single_margin(fx_pair=str(fx_pair), amount=value, domestic=domestic)

        return margin

    def _calc_single_margin(self, fx_pair: str, amount: float, domestic: Currency):
        vol = self._sqrt_hp * self._spot_vols.vol_spot(name=fx_pair)  # annualized vol * length of holding period

        # Compute VaR
        val_at_risk = amount * norm.ppf(1 - self._var_level,
                                        loc=0,
                                        scale=vol)

        # Convert to domestic
        return abs(self._spot_fx_cache.convert_value(val_at_risk,
                                                     from_currency=CustomCurrency(fx_pair[-3:]),
                                                     to_currency=domestic))
