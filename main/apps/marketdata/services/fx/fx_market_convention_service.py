from functools import lru_cache

from django.db import ProgrammingError
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import FxMarketConverter

from main.apps.marketdata.models.fx.fx_market_convention import FxMarketConvention


class FxMarketConventionService(object):
    """
    Service that can be used to get information about FX market conventions.
    """

    @lru_cache(maxsize=2)
    def make_fx_market_converter(self, is_hedge_supported_only: bool = True) -> FxMarketConverter:
        """
        Create an FxMarketConverter, which acts as a cached copy of the FxMarketConventionService.
        """
        traded_pairs = {it.pair: it.min_lot_size for it in
                        FxMarketConvention.get_conventions(is_supported_only=is_hedge_supported_only)}

        return FxMarketConverter(traded_pairs=traded_pairs)
