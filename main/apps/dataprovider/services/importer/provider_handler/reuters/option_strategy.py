import logging
from typing import Optional, Sequence

import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler.reuters.option import ReutersOptionHandler
from main.apps.marketdata.models import FxOptionStrategy

logger = logging.getLogger(__name__)

 
class ReutersOptionStrategyHandler(ReutersOptionHandler):
    model: FxOptionStrategy

    def create_models_with_df(self) -> list:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                tenor=row["tenor"],
                name=row["name"],
                strategy=row["strategy"],
                offset=row["offset"],
                bid_value=row["Bid"] if "Bid" in row else None,
                ask_value=row["Ask"] if "Ask" in row else None,
                mid_value=row["Close"],
                data_cut_id=row['DataCutId']
            )
            for index, row in self.df.iterrows() if row['FxPairId'] > 0
        ]

    def get_insert_only_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id',
            'tenor',
            'name',
            'strategy',
            'offest',
            'bid_value',
            'ask_value',
            'mid_value',
            'data_cut_id'
        ]

    def transform_data(self) -> pd.DataFrame:
        option_strategy_regrex = "(ATM|Put|Call|Bfly|RR)"
        option_offset_regrex = "(10D|25D|45D|10)"
        # rename
        name_map = {
            'O=R': 'ATM',
            'O=': 'ATM',
            '10P': 'Put10D',
            '25P': 'Put25D',
            '45P': 'Put45D',
            '10C': 'Call10D',
            '25C': 'Call25D',
            '45C': 'Call45D',
            'BF': 'Bfly25D',
            'RR': 'RR25D',
            'B10': 'Bfly10D',
            'R10': 'RR10D',
        }
        for key, val in name_map.items():
            self.df["name"] = self.df["name"].str.replace(key, val, regex=True)

        # extract strategy and offset from name
        self.df["strategy"] = self.df["name"].str.extract(option_strategy_regrex)
        self.df["offset"] = self.df["name"].str.extract(option_offset_regrex).fillna("0")

        # filter out unecessary elements
        self.df = self.df.loc[self.df['strategy'].isin(["ATM","Bfly","RR"])]
        self.df.drop_duplicates(subset=["date", "FxPair", "tenor", "name"], keep="first", inplace=True)
        return self.df

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id',
            'tenor',
            'name'
        ]

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        list_df = []
        for name in ["Bfly", "ATM", 'RR']:
            filt = (self.df['FxPair'] == pair) & (self.df['name'] == name)
            df_temp = self.df.loc[filt].copy()
            if name in ["RR"]:
                df_temp.loc[:, "Close"] = -1 * df_temp.loc[:, "Close"]
            df_temp["FxPair"] = inv_pair
            df_temp["FxPairId"] = self.fx_pair_id_map[inv_pair]
            list_df.append(df_temp)

        df_inv_pair = pd.concat(list_df, axis=0)
        df_new = pd.concat([df_new, df_inv_pair], axis=0)
        return df_new
