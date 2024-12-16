from typing import Tuple, Optional, List

from hdlib.DateTime import Date
from main.apps.currency.models import FxPair
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.util import ActionStatus

PrimaryKey = int


class MarketDataAPIService:
    @staticmethod
    def get_fx_eod_spot_time_series(fxpair_pk: PrimaryKey,
                                    start_date: Date,
                                    end_date: Date) -> Tuple[ActionStatus, Optional[List[Tuple[Date, float]]]]:
        fx_pair_ = FxPair.get_pair(fxpair_pk)
        if not fx_pair_:
            return ActionStatus.log_and_error(f"Could not find Fx Pair pk={fxpair_pk}."), None
        return ActionStatus.log_and_success(f"Got time series for Fx Pair pk={fxpair_pk}."), \
               FxSpotProvider().get_eod_spot_time_series(start_date=start_date,
                                                         end_date=end_date,
                                                         fx_pair=fx_pair_)
