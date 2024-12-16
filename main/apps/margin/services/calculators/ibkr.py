import numpy as np
from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache

from main.apps.currency.models import Currency
from main.apps.margin.services.calculators import MarginCalculator
from main.apps.margin.services.calculators import MarginRatesCache

import logging

logger = logging.getLogger(__name__)
class IBMarginCalculator(MarginCalculator):
    def __init__(self):
        super(IBMarginCalculator, self).__init__()

    def compute_margin(self,
                       cash_positions: CashPositions,
                       domestic: Currency,
                       spot_fx_cache: SpotFxCache,
                       margin_rates: MarginRatesCache,
                       multiplier=2.0) -> float:
        """
        Compute margin for a set of cash positions, with a specified domestic currency (called base currency in IB
        documentation, not to be confused with the base currency of an Fx pair).

        See https://ibkr.info/article/970 for an example of how to calculate margin.
        """
        positive_positions = []
        negative_positions = []

        for currency, amount in cash_positions.cash_by_currency.items():
            if np.abs(amount) < 1e-6:
                logger.warning("Ignoring zero amount for currency %s", currency)
                continue
            if np.isnan(amount):
                logger.warning("Ignoring NaN amount for currency %s", currency)
                continue
            # Convert amount to value in base (domestic) currency.
            value = spot_fx_cache.convert_value(value=amount, from_currency=currency, to_currency=domestic)
            if np.isnan(value):
                raise ValueError(f"could not convert from {currency} to {domestic}")
            rate = margin_rates.get_rate_for_currency(currency=currency, quote=domestic)

            if 0 < amount:
                positive_positions.append(np.array([rate, value]))
            else:
                # Accumulate a *positive* number for the negative position.
                negative_positions.append(np.array([rate, -value]))

        # Sort positive net liquid domestic equivalents by smallest rate to largest rate.
        positive_positions = list(sorted(positive_positions, key=lambda x: x[0]))

        # Calculate the margin requirement on that portion which may be used to off-set the negative net liq value
        margin = 0

        it = 0
        for rate1, negative_position in sorted(negative_positions, reverse=True, key=lambda x: x[1]):
            while it < len(positive_positions):
                rate2, amount = positive_positions[it]
                haircut = rate2
                # Start with the largest negative currency balance.
                if negative_position < amount:
                    # We only have to use part of this position to cover the remaining negative positions.
                    positive_positions[it][1] -= negative_position
                    margin += haircut * negative_position
                    break
                else:
                    # We consume the entire positive position, and need to consume more to cover the negative.
                    negative_position -= amount
                    positive_positions[it][1] = 0
                    margin += haircut * amount
                    it += 1

        return margin * multiplier
