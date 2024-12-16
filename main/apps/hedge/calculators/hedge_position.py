from hdlib.Hedge.Cash.CashPositions import CashPositions
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import SpotFxCache
from main.apps.currency.models import Currency


class HedgePositionCalculator:

    def get_total_value(self,
                        spot_fx_cache: SpotFxCache,
                        cash_positions: CashPositions,
                        domestic: Currency,
                        ignore_domestic: bool = True
                        ) -> float:
        """
        Get the total value in domestic currency of existing hedging positions for an account or the entire company
        :param spot_fx_cache: SpotFxCache
        :param ignore_domestic: bool, if true ignore all holdings in domestic currency
        :return: the account value in the domestic currency
        """
        total = 0
        for currency, value in cash_positions.cash_by_currency.items():
            # If only counting 'directional' positions, exclude the value of domestic holdings.
            if currency == domestic and ignore_domestic:
                continue
            total += spot_fx_cache.convert_value(value=value, to_currency=domestic, from_currency=currency)
        return total


