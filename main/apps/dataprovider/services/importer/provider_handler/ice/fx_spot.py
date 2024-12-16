import logging
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from main.apps.core.models import Config
from main.apps.currency.models import FxPair
from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models.fx.rate import FxSpot

logger = logging.getLogger(__name__)

 
class IceFxSpotHandler(IceHandler):
    model: FxSpot
    HOME_CURRENCIES_PATH = "system/fxpair/home_currencies"
    TRIANGULATION_CURRENCIES_PATH = "system/fxpair/triangulation_currencies"

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        return self.df

    def transform_data(self) -> pd.DataFrame:
        self.create_reverse_pairs()
        home_currencies = Config.get_config(path=self.HOME_CURRENCIES_PATH).value
        triangulation_currencies = Config.get_config(path=self.TRIANGULATION_CURRENCIES_PATH).value
        combinations = [(x, y) for x in home_currencies for y in triangulation_currencies]

        for home, triang in combinations:
            self.create_triangulation_pairs(home, triang)

        self.df[f"rate_ask-rate_bid"] = self.df[f"Ask"] - self.df[f"Bid"]
        self.df[f"rate_ask-rate"] = self.df[f"Ask"] - self.df[f"Mid"]
        self.df[f"rate-rate_bid"] = self.df[f"Mid"] - self.df[f"Bid"]

        self.df.loc[:, "Anomaly"] = self.df.apply(self._check_anomaly, axis=1)
        cond = self.df["Anomaly"] == True
        if cond.sum() > 0:
            spread = (self.df.loc[cond, "rate_ask-rate_bid"]).abs()
            rate_bid = self.df.loc[cond, "Mid"] - spread / 2
            rate_ask = self.df.loc[cond, "Mid"] + spread / 2
            self.df.loc[cond, "Bid"] = rate_bid
            self.df.loc[cond, "Ask"] = rate_ask
        return self.df

    def create_models_with_df(self) -> Sequence[FxSpot]:
        rows_added = []
        output = []
        for index, row in self.df.iterrows():
            if row["FxPairId"] < 0:
                continue
            if self.model.objects.filter(pair_id=row['FxPairId'], data_cut_id=row['DataCutId']).count() > 0:
                continue
            key = f"{row['DataCutId']}|{row['FxPairId']}"
            if key in rows_added:
                logger.debug(f"{index} - {row['FxPair']} is a duplicate entry")
                continue
            output.append(
                self.model(
                    date=index,
                    pair_id=row["FxPairId"],
                    rate_bid=row["Bid"],
                    rate_ask=row["Ask"],
                    rate=row["Mid"],
                    data_cut_id=row["DataCutId"]
                )
            )
            rows_added.append(f"{row['DataCutId']}|{row['FxPairId']}")
        return output

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
            "Bid": "Ask",
            "Ask": "Bid",
            "Mid": "Mid",
            "Yesterday": "Yesterday",
            "High": "Low",
            "Low": "High"
        }

        for key, val in inv_values_map.items():
            df_inv_pair[val] = (1 / df_temp[key]).replace([np.inf, -np.inf], np.nan).copy()

        df_inv_pair["FxPair"] = inv_pair
        df_inv_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
        df_new = pd.concat([df_new, df_inv_pair], axis=0)
        return df_new

    def create_triangulation_pairs(self, home: str, triang: str):
        for idx, row in self.df.iterrows():
            if row["FxPairId"] >= 0:
                continue
            else:
                raise ValueError(f"Fx Pair related to {row['SDKey']} is not registered!")

        fxpairs = {FxPair.get_pair(i).name: FxPair.get_pair(i) for i in self.df["FxPairId"].unique()}

        try:
            home_triang_df = self.df[self.df["FxPairId"] == fxpairs[F"{home}/{triang}"].id]
        except:
            logger.warning(f"FxPair {home}/{triang} is not available! Skipping the triangulation pairs.")
            return

        other_home_pairs = {name: pair for name, pair in fxpairs.items() if
                            name.endswith(f"/{home}") and name != f"{triang}/{home}"}
        additional_pairs_dfs = []
        for name, pair in other_home_pairs.items():
            other_home_df = self.df[self.df["FxPairId"] == pair.id].copy()
            other = name.split('/')[0]
            # Calculate other/triang pairs
            other_triang_df = other_home_df.copy()
            fxpair_other_triang = FxPair.get_pair(f"{other}/{triang}")
            if fxpair_other_triang is None:
                raise ValueError(f"FxPair {other}/{triang} is not registered!")

            other_triang_df["FxPairId"] = fxpair_other_triang.id
            other_triang_df["FxPair"] = f"{other}{triang}"
            for col in ("Mid", "Ask", "Bid", "High", "Low", "Yesterday"):
                other_triang_df[col] = other_home_df[col] * home_triang_df[col]
            additional_pairs_dfs.append(other_triang_df)

            # Calculate triang/other pairs
            triang_other_df = other_triang_df.copy()
            fxpair_triang_other = FxPair.get_pair(f"{triang}/{other}")
            if fxpair_triang_other is None:
                raise ValueError(f"FxPair {triang}/{other} is not registered!")

            triang_other_df["FxPairId"] = fxpair_triang_other.id
            triang_other_df["FxPair"] = f"{triang}{other}"
            triang_other_df["Mid"] = 1 / other_triang_df["Mid"]
            triang_other_df["Ask"] = 1 / other_triang_df["Bid"]
            triang_other_df["Bid"] = 1 / other_triang_df["Ask"]
            triang_other_df["High"] = 1 / other_triang_df["Low"]
            triang_other_df["Low"] = 1 / other_triang_df["High"]
            triang_other_df["Yesterday"] = 1 / other_triang_df["Yesterday"]
            additional_pairs_dfs.append(triang_other_df)
        self.df = pd.concat([self.df] + additional_pairs_dfs, axis=0)

    @staticmethod
    def _check_anomaly(series: pd.Series) -> bool:
        for name in ["rate_ask-rate_bid", "rate_ask-rate", "rate-rate_bid"]:
            if series[name] < 0:
                return True
        return False
