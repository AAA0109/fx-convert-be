from datetime import datetime, time
from typing import List

from pytz import timezone
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.backend.calendar_utils import get_spot_dt


class MarketSpotDateProvider:

    TZ = timezone('America/New_York')
    CUT_TIME_HRS = 16

    def populate_pairs_spot_dates(self, pairs:List[FxPair]) -> dict:

        spot_dates = []

        for pair in pairs:
            spot_date, settlement_days, spot_days = get_spot_dt(mkt=pair.market)
            spot_dates.append({
                'pair': pair.market,
                'spot_date': spot_date,
                'executable_time': self.TZ.localize(datetime.combine(
                    spot_date, time(self.CUT_TIME_HRS))).astimezone(timezone('UTC'))
            })

        return { 'spot_dates': spot_dates }
