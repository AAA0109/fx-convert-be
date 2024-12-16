import pandas as pd
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from hdlib.DateTime.Date import Date

from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.marketdata.services.initial_marketdata import ccy_triangulate_rate, get_ccy_legs
from main.apps.oems.backend.ccy_utils import determine_rate_side


class HistoricalSpotDataProvider:
    pair:FxPair
    invert:bool
    triangulate:bool

    def __init__(self, pair:FxPair, invert:Optional[bool] = None,
                triangulate:Optional[bool] = None) -> None:
        self.pair = pair

        self.invert = invert
        if self.invert is None:
            fx_pair, side = determine_rate_side( pair.base_currency, pair.quote_currency )
            self.invert = side == 'Sell'

        self.triangulate = triangulate
        if self.triangulate is None:
            self.triangulate = 'USD' not in self.pair.market

    def to_date_indexed_dict(self, items:List[list]) -> Dict[Date, float]:
        result = {}
        for item in items:
            dt = Date.from_datetime(item[0])
            result[dt] = item[1]
        return result

    def get_triangulated_data(self, start_date:datetime, end_date:datetime) -> List[list]:
        triangulated_data = []

        base_ccy, cntr_ccy, base_multiply, cntr_multipy = get_ccy_legs(self.pair.market)
        base_fx_pair = FxPair.get_pair(base_ccy)
        cntr_fx_pair = FxPair.get_pair(cntr_ccy)

        base_data = FxSpotProvider().get_eod_spot_time_series(start_date=start_date,
                                                                end_date=end_date,
                                                                fx_pair=base_fx_pair)
        cntr_data = FxSpotProvider().get_eod_spot_time_series(start_date=start_date,
                                                                end_date=end_date,
                                                                fx_pair=cntr_fx_pair)

        base_data = self.to_date_indexed_dict(items=base_data)
        cntr_data = self.to_date_indexed_dict(items=cntr_data)

        for key, value in base_data.items():
            dt = key
            base_rate = value
            cntr_rate = cntr_data.get(dt)

            if not cntr_rate: continue

            rate = None

            try:
                rate = ccy_triangulate_rate(base_ccy=base_ccy, base_rate=base_rate, cntr_ccy=cntr_ccy,
                                      cntr_rate=cntr_rate, base_multiply=base_multiply, cntr_multipy=cntr_multipy)
                if self.invert: rate = 1.0 / rate
            except Exception as e:
                pass

            out_row = [key, rate]
            triangulated_data.append(out_row)
        return triangulated_data

    def get_non_triangulated_data(self, start_date:datetime, end_date:datetime) -> List[list]:
        non_triangulated_data = []
        data = FxSpotProvider().get_eod_spot_time_series(start_date=start_date,
                                                                end_date=end_date,
                                                                fx_pair=self.pair)
        data = self.to_date_indexed_dict(items=data)

        for key, value in data.items():
            rate = None
            try:
                rate = 1.0 / value if self.invert else value
            except:
                pass
            out_row = [key, rate]
            non_triangulated_data.append(out_row)
        return non_triangulated_data

    def get_historical_spot_data(self, start_date:datetime, end_date:datetime) -> List[list]:
        if self.triangulate:
            return self.get_triangulated_data(start_date=start_date, end_date=end_date)
        return self.get_non_triangulated_data(start_date=start_date, end_date=end_date)


class MovingAverageProvider:
    pair:FxPair
    invert:bool
    triangulate:bool
    n_days:int = 50

    def __init__(self, pair:FxPair, invert:Optional[bool] = None,
                triangulate:Optional[bool] = None) -> None:
        self.pair = pair

        self.invert = invert
        if self.invert is None:
            fx_pair, side = determine_rate_side( pair.base_currency, pair.quote_currency )
            self.invert = side == 'Sell'

        self.triangulate = triangulate
        if self.triangulate is None:
            self.triangulate = 'USD' not in self.pair.market

        self.columns = ['date', 'rate']


    def set_moving_avg_window(self, start_date:datetime, end_date:datetime) -> int:
        """
        Set moving average window
        if date difference <= 6 months then ma window = 20 days
        elif date difference > 6 months and <= 2.5 years then ma window = 50 days
        elif date difference > 2.5 years then ma window = 200 days
        """

        diff = relativedelta(end_date, start_date)
        months_diff = diff.years * 12 + diff.months

        if months_diff <= 6:
            self.n_days = 20
        elif months_diff > 6 and months_diff <= 2.5 * 12:
            self.n_days = 50
        elif months_diff > 2.5 * 12:
            self.n_days = 200
        return self.n_days

    def calculate_moving_average_using_method(self, df:pd.DataFrame, window:Optional[int] = None) -> pd.DataFrame:
        """
        Calculate moving average for spot data using different moving average type
        if window or n_days <= 20 the use exponentially weighted moving average
        else use simple moving average
        """

        if window is None:
            window = self.n_days

        if window <= 20:
            for col in self.columns:
                if col != 'date':
                    df[f'{col}_ma'] = df[col].ewm(span=window, adjust=False).mean()
            return df

        for col in self.columns:
            if col != 'date':
                df[f'{col}_ma'] = df[col].rolling(window=window).mean()
        return df

    def calculate_moving_average(self, start_date:datetime, end_date:datetime, spot_data:Optional[List[list]] = None) -> dict:
        """
        Calculate moving average for spot data
        spot data format: List[[datetime, open, high, low, close]]
        """

        data = spot_data
        if data is None:
            self.set_moving_avg_window(start_date=start_date, end_date=end_date)
            end_time = end_date
            start_time = start_date - timedelta(days=2 * self.n_days)

            spot_data_provider = HistoricalSpotDataProvider(pair=self.pair, invert=self.invert, triangulate=self.triangulate)
            data = spot_data_provider.get_historical_spot_data(start_date=start_time, end_date=end_time)

        df = pd.DataFrame(
            data=data,
            columns=self.columns
        )

        for col in self.columns:
            if col != 'date':
                df[col] = df[col].fillna(df[col].median())

        df = self.calculate_moving_average_using_method(df=df, window=self.n_days)

        df.replace({float('nan'): None}, inplace=True)

        data = {}
        for index, row in df.iterrows():
            if row[1] is None:
                continue
            data[row[0].date()] = {
                'rate_ma': row[2],
            }

        return data

    def get_moving_avg_data_by_date(self, ma_data:dict, key:date, threshold_date:date) -> Optional[dict]:
        """
        Find moving average data by date key
        If no data found then find data for closest previous date
        """
        ma = ma_data.get(key, None)
        max_back_days = 31
        if ma is None:
            i = 1
            while ma is None and i <= max_back_days:
                key = key - timedelta(days=i)
                ma = ma_data.get(key, None)
                i += 1
        return ma
