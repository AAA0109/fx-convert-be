import logging
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from django.db.models import F

from main.apps.dataprovider.mixins.services.importer.provider_handler.fx.forawrd import FxForwardMixin
from main.apps.dataprovider.services.importer.provider_handler import ReutersHandler
from main.apps.marketdata.models import FxForward, FxSpot

logger = logging.getLogger(__name__)
 

class ReutersFxForwardHandler(FxForwardMixin, ReutersHandler):
    model: FxForward
    def transform_data(self) -> pd.DataFrame:
        try:
            vals_tobe_fixed = ['Ask High', "Bid High", "Low Ask", "Low Bid", "Open Ask", "Open Bid", "Ask", "Bid",
                               "Universal Ask Price", "Universal Bid Price", "Average of Bid and Ask",
                               "Universal Close Price"]

            self.df.loc[:, vals_tobe_fixed] = self.df.loc[:, vals_tobe_fixed].replace(",", "", regex=True).astype(
                "float64")
            self.df["tenor"] = self.df["Instrument ID"].str.slice(3, 6).replace("=", "", regex=True)

            # Reverse Ask and Bid if Ask < Bid
            reversed_ask_bid = self.df['Universal Ask Price'] < self.df['Universal Bid Price']
            self.df.loc[reversed_ask_bid, ['Universal Ask Price', 'Universal Bid Price']] = (
                self.df.loc[reversed_ask_bid, ['Universal Bid Price', 'Universal Ask Price']].values
            )

            self.df.loc[:, 'fwd_points'] = self.df.loc[:, 'Universal Close Price']
            self.df.loc[:, 'spread'] = self.df.loc[:, 'Universal Ask Price'] - self.df.loc[:, 'Universal Bid Price']
            for pair, divisor in self.get_pair_map().items():
                if divisor == 1:
                    continue
                cond = self.df['Currency'] == pair
                self.df.loc[cond, 'fwd_points'] = self.df.loc[cond, 'Universal Close Price'] / divisor
                self.df.loc[cond, 'spread'] = self.df.loc[cond, 'spread'] / divisor

            self.df["fwd_points_bid"] = self.df["fwd_points"] - (self.df['spread'] / 2)
            self.df["fwd_points_ask"] = self.df["fwd_points"] + (self.df['spread'] / 2)
            self.df.drop_duplicates(subset=["date", "FxPair", "tenor"], keep="first", inplace=True)
        except:
            print("done")
        return self.df

    def before_create_models_with_df(self):
        data_cut_ids = self.df['DataCutId'].unique()
        fx_pair_ids = self.df['FxPairId'].unique()
        fx_spot_qs = FxSpot.objects.filter(
            data_cut_id__in=data_cut_ids, pair_id__in=fx_pair_ids
        ).annotate(
            spot_date=F('date'), spot_rate=F('rate'), spot_rate_bid=F('rate_bid'), spot_rate_ask=F('rate_ask')
        ).all().values()
        fx_spot_df = pd.DataFrame(fx_spot_qs)
        fx_spot_df.drop(columns=['date', 'rate', 'rate_bid', 'rate_ask'], inplace=True)
        merged_df = pd.merge(
            self.df,
            fx_spot_df,
            how='inner',
            left_on=['DataCutId', 'FxPairId'],
            right_on=['data_cut_id', 'pair_id']
        )
        merged_df.set_index('date', inplace=True)
        merged_df.sort_index(inplace=True)
        merged_df['rate'] = merged_df['fwd_points'] + merged_df['spot_rate']
        merged_df['rate_bid'] = merged_df['fwd_points_bid'] + merged_df['spot_rate']
        merged_df['rate_ask'] = merged_df['fwd_points_ask'] + merged_df['spot_rate']

        self.df = merged_df[['Currency', 'FxPair', 'FxPairId', 'tenor', 'rate', 'rate_bid', 'rate_ask',
                             'fwd_points', 'fwd_points_bid', 'fwd_points_ask', 'DataCutId', 'spot_rate']]
        self.create_reverse_pairs()
        self.clean_data()
        pass

    def create_models_with_df(self) -> list:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                tenor=row["tenor"],
                rate=row['rate'],
                rate_bid=row['rate_bid'],
                rate_ask=row['rate_ask'],
                fwd_points=row["fwd_points"],
                fwd_points_bid=row["fwd_points_bid"],
                fwd_points_ask=row["fwd_points_ask"],
                depo_base=0,
                depo_quote=0,
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row['FxPairId'] > 0
        ]

    def clean_data(self) -> pd.DataFrame:
        super().clean_data()
        # drop rows with missing data for all columns
        columns_to_clean = ['rate', 'rate_bid', 'rate_ask', 'fwd_points', 'fwd_points_bid', 'fwd_points_ask']
        dropna_columns = []
        for column in columns_to_clean:
            if column in self.df.columns:
                dropna_columns.append(column)
        self.df.dropna(subset=dropna_columns, inplace=True)

    def get_insert_only_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id',
            'tenor',
            'rate',
            'rate_bid',
            'rate_ask',
            'fwd_points',
            'fwd_points_bid',
            'fwd_points_ask',
            'depo_base',
            'depo_quote',
            'data_cut_id'
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id',
            'tenor'
        ]

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        list_df = []
        for tenor in self.df["tenor"].unique():
            filt = (self.df["FxPair"] == pair) & (self.df["tenor"] == tenor)
            df_temp = self.df.loc[filt].copy()
            df_inv_pair = df_temp.copy()

            df_inv_pair["FxPair"] = inv_pair
            df_inv_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
            column_mapping = (
                ("spot_rate", "spot_rate"),
                ("rate", "rate"),
                ("rate_bid", "rate_ask"),
                ("rate_ask", "rate_bid")
            )
            for key, value in column_mapping:
                df_inv_pair[key] = (1 / df_temp[value]).replace([np.inf, -np.inf], np.nan)

            df_inv_pair['fwd_points_bid'] = df_inv_pair['rate_bid'] - df_inv_pair['spot_rate']
            df_inv_pair['fwd_points_ask'] = df_inv_pair['rate_ask'] - df_inv_pair['spot_rate']
            df_inv_pair['fwd_points'] = (df_inv_pair['fwd_points_ask'] + df_inv_pair['fwd_points_bid']) / 2
            list_df.append(df_inv_pair)

        df_new = pd.concat([df_new] + list_df, axis=0)
        return df_new

    def get_pair_map(self):
        return {
            'CAD': 14000,  # 1000,
            'MXN': 1,
            'JPY': 100,  # 100,
            'CNY': 1,  # 1000,
            'KRW': 200,  # 1000,
            'SGD': 19000,  # 1000,
            'EUR': 9800,  # 1000,
            'AUD': 10000,  # 1000,
            'GBP': 6800,  # 1000,

        }


"""
'CNH': 1, all ice
'HKD': 1, all ice
'ILS': 1, all ice
'ZAR': 1,  # only reuter
'IDR': 1,  # only reuter
'INR': 1,  # only reuter
'CHF': 1,  # only reuter
'BRL': 1,  # not available
'RUB': 1,  # only reuter
'ANG': 1,  # only reuter
'SAR': 1,  # only reuter
'ARS': 1,  # not available
'TRY': 1  # only reuter
"""
