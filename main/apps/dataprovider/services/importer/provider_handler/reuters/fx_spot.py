import logging
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler import ReutersHandler
from main.apps.marketdata.models.fx.rate import FxSpot

logger = logging.getLogger(__name__)

 
class ReutersFxSpotHandler(ReutersHandler):
    model: FxSpot

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        vals_tobe_fixed = ["Open Ask", "Open Bid", "Open", "Low Ask", "Low Bid", "Low", "Ask High", "Bid High", "High",
                           "Close"]
        self.df.loc[:, vals_tobe_fixed] = self.df.loc[:, vals_tobe_fixed].replace(",", "", regex=True).astype(
            "float64")

        # the original Open, Low, High are either 2x or 0.5x of Close price
        # the following calculation is to approach the real value
        self.df['Open'] = self.df[['Open Ask', 'Open Bid']].mean(axis=1)
        self.df['Low'] = self.df[['Low Ask', 'Low Bid']].mean(axis=1)
        self.df['High'] = self.df[['Ask High', 'Bid High']].mean(axis=1)

        self.df.drop_duplicates(subset=["date", "FxPair"], keep="first", inplace=True)
        return self.df

    def create_models_with_df(self) -> list:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                rate=row["rate"],
                rate_bid=row["rate_bid"],
                rate_ask=row["rate_ask"],
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row['FxPairId'] > 0
        ]

    def get_insert_only_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id',
            'rate',
            'rate_bid',
            'rate_ask',
            'data_cut_id'
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id'
        ]

    def transform_data(self) -> pd.DataFrame:
        self.create_reverse_pairs()
        self.df['rate'] = (self.df["Low"] + self.df["High"]) / 2
        self.df['rate_bid'] = (self.df["Low Bid"] + self.df["Bid High"]) / 2
        self.df['rate_ask'] = (self.df["Low Ask"] + self.df["Ask High"]) / 2
        rate_ask_computed = 2 * self.df['rate'] - self.df['rate_bid']
        rate_bid_computed = 2 * self.df['rate'] - self.df['rate_ask']
        self.df['rate_ask'] = rate_ask_computed.where(
            self.df['rate_ask'].isna() &
            self.df['rate_bid'].notna() &
            self.df['rate'].notna(),
            other=self.df['rate_ask']
        )
        self.df['rate_bid'] = rate_bid_computed.where(
            self.df['rate_bid'].isna() &
            self.df['rate_ask'].notna() &
            self.df['rate'].notna(),
            other=self.df['rate_bid']
        )
        self.df[f"rate_ask-rate_bid"] = self.df[f"rate_ask"] - self.df[f"rate_bid"]
        self.df[f"rate_ask-rate"] = self.df[f"rate_ask"] - self.df[f"rate"]
        self.df[f"rate-rate_bid"] = self.df[f"rate"] - self.df[f"rate_bid"]

        self.df.loc[:, "Anomaly"]=self.df.apply(self._check_anomaly,axis=1)
        cond = self.df["Anomaly"]==True
        if cond.sum()>0:
            spread = (self.df.loc[cond,"rate_ask-rate_bid"]).abs()
            rate_bid = self.df.loc[cond,"rate"]-spread/2
            rate_ask = self.df.loc[cond,"rate"]+spread/2
            self.df.loc[cond, "rate_bid"]=rate_bid
            self.df.loc[cond, "rate_ask"]=rate_ask
        return self.df

    def clean_data(self) -> pd.DataFrame:
        super().clean_data()
        self.df.dropna(subset=['rate', 'rate_ask', 'rate_bid'], inplace=True)
        pass

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        filt = (self.df["FxPair"] == pair)
        df_temp = self.df.loc[filt].copy()
        df_inv_pair = df_temp.copy()
        inv_values_map = {
            "Open Bid": "Open Ask",
            "Open Ask": "Open Bid",
            "Open": "Open",
            "Close": "Close",

            "Bid High": "Low Ask",
            "Ask High": "Low Bid",
            "High": "Low",

            "Low Bid": "Ask High",
            "Low Ask": "Bid High",
            "Low": "High"
        }

        for key, val in inv_values_map.items():
            df_inv_pair[val] = (1 / df_temp[key]).replace([np.inf, -np.inf], np.nan).copy()

        df_inv_pair["FxPair"] = inv_pair
        df_inv_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
        df_new = pd.concat([df_new, df_inv_pair], axis=0)
        return df_new

    def rename_column(self):
        self.df.rename(columns={"Currency": "Instrument ID"}, inplace=True)

    @staticmethod
    def _check_anomaly(series: pd.Series) -> bool:
        for name in ["rate_ask-rate_bid", "rate_ask-rate", "rate-rate_bid"]:
            if series[name] < 0:
                return True
        return False
