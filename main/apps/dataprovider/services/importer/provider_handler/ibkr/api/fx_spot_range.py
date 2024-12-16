from typing import Sequence, Optional
import pytz

from hdlib.DateTime.Date import Date

import pandas as pd

from main.apps.marketdata.models import FxSpotRange
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.base import IbkrApiHandler
from ib_insync import *


class IbkrFxSpotRangeApiHandler(IbkrApiHandler):
    model: FxSpotRange

    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        if self.client is None:
            return
        now = Date.now()
        tz = pytz.timezone('US/Eastern')
        date = Date(now.year, now.month, now.day, 17, 0, 0)
        date = tz.localize(date)
        self.df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "FxPair", "FxPairId"])
        if self.client is None:
            return
        contracts = []
        trading_class_mapping = {}
        for fx_pair in self.get_supported_pairs():
            pair = fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic
            contract = self.api.get_contract(type="forex", symbol=pair)
            contracts.append(contract)
            trading_class_mapping[f"{fx_pair.base_currency.mnemonic}.{fx_pair.quote_currency.mnemonic}"] = fx_pair.id
        self.client.qualifyContracts(*contracts)
        for contract in contracts:
            barList = []
            bars = self.client.reqHistoricalData(
                contract,
                endDateTime=date,
                durationStr="60 S",
                barSizeSetting="1 min",
                whatToShow="BID_ASK",
                useRTH=True,
                formatDate=1)
            barList.append(bars)
            allBars = [b for bars in reversed(barList) for b in bars]
            if not allBars:
                continue
            pair_df = util.df(allBars)
            if not pair_df.empty:
                pair_df["FxPair"] = contract.symbol + contract.currency
                pair_df["FxPairId"] = trading_class_mapping[contract.tradingClass]

            self.df = pd.concat([self.df, pair_df])
        return self.df

    def before_handle(self) -> pd.DataFrame:
        self.df["date"] = self.df["date"].apply(lambda x: x.tz_localize('UTC'))
        self.df["_index"] = self.df["date"]
        self.df.set_index("_index", inplace=True)

    def create_models_with_df(self) -> Sequence[FxSpotRange]:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                open=row["open"],
                open_bid=None,
                open_ask=None,
                low=row["low"],
                low_bid=None,
                low_ask=None,
                high=row["high"],
                high_bid=None,
                high_ask=None,
                close=row["close"],
                close_bid=None,
                close_ask=None,
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["FxPairId"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "pair_id"
        ]
