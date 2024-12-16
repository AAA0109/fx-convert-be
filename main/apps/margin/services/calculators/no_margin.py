from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from main.apps.currency.models import Currency
from main.apps.margin.services.calculators import MarginCalculator, MarginRatesCache


class MarginCalculator_NoMargin(MarginCalculator):
    def compute_margin(self, cash_positions: CashPositions, domestic: Currency, spot_fx_cache: SpotFxCache,
                       margin_rates: MarginRatesCache, multiplier=2.0) -> float:
        return 0
