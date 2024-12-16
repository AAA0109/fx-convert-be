import logging
import pandas as pd

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db.models import Avg
from django.db.models.functions import TruncHour

from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models import CorpayFxSpot
from main.apps.oems.api.dataclasses.liquidity_insight import LiquidityStatus

from typing import List, Optional

logger = logging.getLogger(__name__)


class SpreadProvider:
    fx_pair:FxPair
    avg_monthly_spot_data:List[dict]
    start_date:datetime
    end_date:datetime
    dow_hly_grouped_df_mean:pd.DataFrame
    dow_hly_grouped_df_quantile:pd.DataFrame

    def __init__(self, fx_pair:FxPair, ref_date:Optional[datetime]) -> None:
        self.fx_pair = fx_pair
        ref_date = ref_date if ref_date else datetime.now()
        self.end_date = ref_date.replace(minute=0, second=0, microsecond=0)
        self.start_date = self.end_date + relativedelta(months=-1)

        hourly_data = []

        if self.fx_pair.base_currency != self.fx_pair.quote_currency:
            hourly_data = CorpayFxSpot.objects.filter(
                pair=self.fx_pair,
                date__gte=self.start_date,
                date__lte=self.end_date,
            ).annotate(
                hly_date=TruncHour('date'),
            ).values('hly_date').annotate(
                hly_rate_bid=Avg('rate_bid'),
                hly_rate=Avg('rate'),
                hly_rate_ask=Avg('rate_ask'),
                hly_spread=Avg('rate_ask') - Avg('rate_bid')
            ).order_by('hly_date')

        rows = []
        columns = [
            'hly_date',
            'hly_rate_ask',
            'hly_rate',
            'hly_rate_bid',
            'hly_spread'
        ]

        for item in list(hourly_data):
            rows.append([
                item['hly_date'],
                item['hly_rate_ask'],
                item['hly_rate'],
                item['hly_rate_bid'],
                item['hly_spread']]
            )

        df = pd.DataFrame(
            rows,
            columns=columns
        )

        if not df.empty:
            dow_hly_grouped = df.groupby([df['hly_date'].dt.day_of_week, df['hly_date'].dt.hour])
            self.dow_hly_grouped_df_mean = dow_hly_grouped.mean()
            self.dow_hly_grouped_df_quantile = dow_hly_grouped.quantile([0.33, 0.66])

    def get_average_spread(self, weekday:int, hour:int) -> Optional[float]:
        try:
            return self.dow_hly_grouped_df_mean['hly_spread'][(weekday, hour)]
        except Exception as e:
            return None

    def get_liquidity_status(self, weekday:int, hour:int, spread:Optional[float]) -> Optional[str]:
        if not spread:
            try:
                spread = self.dow_hly_grouped_df_mean['hly_spread'][(weekday, hour)]
            except Exception as e:
                return None

        try:
            q1 = self.dow_hly_grouped_df_quantile['hly_spread'][(weekday, hour, 0.33)]
            q2 = self.dow_hly_grouped_df_quantile['hly_spread'][(weekday, hour, 0.66)]

            if spread <= q1:
                return LiquidityStatus.GOOD.value
            elif spread > q1 and spread <= q2:
                return LiquidityStatus.ACCEPTABLE.value
            else:
                return LiquidityStatus.POOR.value
        except Exception as e:
            return None

    def get_current_time_spread(self, dt:datetime) -> Optional[float]:
        start = dt.replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        spot_data = CorpayFxSpot.objects.filter(
            pair=self.fx_pair,
            date__gte=start,
            date__lt=end,
        ).annotate(
            hly_date=TruncHour('date'),
        ).values('hly_date').annotate(
            hly_rate_bid=Avg('rate_bid'),
            hly_rate=Avg('rate'),
            hly_rate_ask=Avg('rate_ask'),
            hly_spread=Avg('rate_ask') - Avg('rate_bid')
        )

        if spot_data.count() == 0:
            try:
                spread_value = self.dow_hly_grouped_df_mean['hly_spread'][(dt.weekday(), dt.hour)]
                return spread_value
            except Exception as e:
                return None

        return list(spot_data)[0].get('hly_spread')

    def no_spot_data_return_condition(self, weekday:int, hour:int) -> str:
        logger.warning(f"Can't find spot data on weekday:{weekday} and hour:{hour}."
                           f"Returning Poor Liquidity")
        return LiquidityStatus.POOR.value
