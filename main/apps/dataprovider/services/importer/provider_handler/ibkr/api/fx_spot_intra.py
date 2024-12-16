import math
from datetime import datetime
from datetime import timedelta
from typing import Sequence, Optional, Type

import numpy as np
import pandas as pd
import pytz
from django.db import models
from ib_insync import util

from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.base import IbkrApiHandler
from main.apps.marketdata.models import FxSpotIntraIBKR, DataCut

UTC_TIME_ZONE = pytz.timezone('UTC')
EST_TIME_ZONE = pytz.timezone('US/Eastern')


class IbkrFxSpotIntraIBKRApiHandler(IbkrApiHandler):
    model: FxSpotIntraIBKR

    def __init__(self, data_cut_type: DataCut.CutType, model: Type[models.Model]):
        super().__init__(data_cut_type=data_cut_type, model=model)
        self._interval_minutes: int = 15
        self.look_back_days: int = 7
        self.reference_time: Optional[datetime] = None

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        if self.client is None:
            return
        time = self.reference_time or datetime.now(pytz.utc).astimezone(UTC_TIME_ZONE)
        earliest_date = time - timedelta(days=self.look_back_days)

        historical_data = self._load_from_ibkr_api(time, earliest_date)
        self.df = self._map_data(historical_data)
        self.df.sort_values("date").reset_index(drop=True)
        self.df = self.df.drop_duplicates(subset=['date', 'FxPairId'])
        return self.df

    def before_handle(self):
        self.fx_pair_id_map = self._get_fx_pair_id_map()
        self.df["_index"] = self.df["date"]
        self.df.set_index("_index", inplace=True)

    def add_data_cut_to_df(self):
        return

    def create_models_with_df(self) -> Sequence[FxSpotIntraIBKR]:
        return [
            self.model(
                date=index,
                rate=row["rate"],
                rate_bid=row["rate_bid"],
                rate_ask=row["rate_ask"],
                pair_id=row["FxPairId"]
            )
            for index, row in self.df.iterrows()
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "pair_id"
        ]

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        filt = (self.df["FxPair"] == pair)
        df_temp = self.df.loc[filt].copy()
        df_inv_pair = df_temp.copy()

        inv_values_map = {
            "rate_bid": "rate_ask",
            "rate_ask": "rate_bid",
            "rate": "rate"
        }

        for key, val in inv_values_map.items():
            df_inv_pair[val] = (1 / df_temp[key]).replace([np.inf, -np.inf], np.nan).copy()

        df_inv_pair["FxPair"] = inv_pair
        df_inv_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
        df_new = pd.concat([df_new, df_inv_pair], axis=0)
        return df_new

    # ==================
    # Private methods
    # ==================
    @staticmethod
    def _map_data(historical_data: pd.DataFrame) -> pd.DataFrame:
        """Map historical data to a new DataFrame schema.
        :param: Original DataFrame containing historical data.
        Returns:
            A new DataFrame containing the mapped data.
        """
        backfill_data = {"date": [], "rate": [], "rate_bid": [], "rate_ask": [], "FxPair": [], "FxPairId": []}
        for index, row in historical_data.iterrows():
            backfill_data["date"].append(index)
            backfill_data["rate"].append((row.open + row.close) / 2)
            backfill_data["rate_bid"].append(row.open)
            backfill_data["rate_ask"].append(row.close)
            backfill_data["FxPair"].append(row.FxPair)
            backfill_data["FxPairId"].append(row.FxPairId)
        backfill_df = pd.DataFrame(backfill_data)
        return backfill_df

    @staticmethod
    def _round_interval(dt: datetime, interval_minutes: int) -> datetime:
        """
        Rounds down a datetime object to the nearest interval of minutes.

        This function takes a datetime object and an integer representing an interval in minutes,
        and returns a new datetime object rounded down to the nearest multiple of the interval.
        :param dt: The original datetime object that needs to be rounded.
        :param interval_minutes:  The interval in minutes to which dt will be rounded down.

        Returns:
        - datetime: A new datetime object that is rounded down to the nearest multiple of interval_minutes.

        Examples:
        If dt = datetime(2023, 9, 18, 21, 37) and interval_minutes = 15,
        the returned datetime would be datetime(2023, 9, 18, 21, 30).
        """
        minutes = math.floor(dt.minute / interval_minutes) * interval_minutes
        return dt.replace(minute=minutes, second=0, microsecond=0)

    def _load_from_ibkr_api(self, now: datetime, earliest_date: datetime) -> pd.DataFrame:
        """Load historical data from the IBKR API.

        :param now: Current datetime.
        :param earliest_missing_dates: The earliest date from which data is missing.

        Returns:
            A DataFrame containing the loaded data.
        """
        historical_data = pd.DataFrame(columns=["date", "open", "high", "low", "close", "FxPair", "FxPairId"])
        contracts = []
        trading_class_mapping = {}
        for fx_pair in self.get_supported_pairs():
            pair = fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic
            contract = self.api.get_contract(type="forex", symbol=pair)
            contracts.append(contract)
            trading_class_mapping[f"{fx_pair.base_currency.mnemonic}.{fx_pair.quote_currency.mnemonic}"] = fx_pair.id
        self.client.qualifyContracts(*contracts)
        for contract in contracts:
            dt = now
            barList = []
            while True:
                bars = self.client.reqHistoricalData(
                    contract,
                    endDateTime=dt.strftime(f'%Y%m%d %H:%M:%S UTC'),
                    durationStr="7 D",
                    barSizeSetting="15 mins",
                    whatToShow="BID_ASK",
                    useRTH=True,
                    formatDate=1)
                barList.append(bars)
                if not bars:
                    break
                dt = (EST_TIME_ZONE.localize(bars[0].date)).astimezone(UTC_TIME_ZONE)
                if dt < earliest_date:
                    break

            allBars = [b for bars in reversed(barList) for b in bars]
            if not allBars:
                continue
            pair_df = util.df(allBars)
            if not pair_df.empty:
                pair_df["FxPair"] = contract.symbol + contract.currency
                pair_df["FxPairId"] = trading_class_mapping[contract.tradingClass]
            historical_data = pd.concat([historical_data, pair_df])

        historical_data['date'] = pd.to_datetime(historical_data['date'])
        historical_data['date'] = historical_data['date'].apply(
            lambda x: EST_TIME_ZONE.localize(x).astimezone(UTC_TIME_ZONE))
        historical_data.set_index('date', inplace=True)
        historical_data.sort_index(inplace=True)
        return historical_data
