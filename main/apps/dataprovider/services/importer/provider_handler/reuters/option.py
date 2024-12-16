import logging
from typing import Sequence, Optional

import pandas as pd
from django.db.models import F

from main.apps.core.utils.date import string2days
from main.apps.dataprovider.services.importer.provider_handler import ReutersHandler
from main.apps.marketdata.models import FxOption
from main.apps.marketdata.models.fx.rate import FxSpot

logger = logging.getLogger(__name__)

 
class ReutersOptionHandler(ReutersHandler):
    model: FxOption

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df = self.df.loc[self.df["FxPairId"] > 0]
        option_tenor_regrex = '(SW|1M|2M|3M|6M|9M|1Y|2Y)'
        option_name_regrex = '(O=|O=R|10P|25P|45P|10C|25C|45C|RR|BF|R10|B10)'
        self.df["tenor"] = self.df["Instrument ID"].str.extract(option_tenor_regrex)
        self.df["expiry_days"] = self.df["tenor"].apply(string2days)
        self.df["name"] = self.df["Instrument ID"].str.extract(option_name_regrex)
        return self.df

    def before_create_models_with_df(self):
        if len(self.df) == 0:
            logger.warning("self.df is empty for this batch!")
        else:
            data_cut_ids = self.df['DataCutId'].unique()
            fx_pair_ids = self.df['FxPairId'].unique()
            fx_spot_qs = FxSpot.objects.filter(
                data_cut_id__in=data_cut_ids, pair_id__in=fx_pair_ids
            ).annotate(
                spot_date=F('date'), spot_rate=F('rate'), spot_rate_bid=F('rate_bid'), spot_rate_ask=F('rate_ask')
            ).all().values()
            fx_spot_df = pd.DataFrame(fx_spot_qs)
            merged_df = pd.merge(
                self.df,
                fx_spot_df[["data_cut_id", "pair_id", "spot_date", "spot_rate", "spot_rate_bid", "spot_rate_ask"]],
                how='inner',
                left_on=['DataCutId', 'FxPairId'],
                right_on=['data_cut_id', 'pair_id']
            )
            merged_df.set_index('date', inplace=True)
            merged_df.sort_index(inplace=True)

            self.df = merged_df.copy()
            self.create_reverse_pairs()
            self.clean_data()

    def create_models_with_df(self) -> Sequence[FxOption]:
        return [
            self.model(
                date=index,
                pair_id=row["FxPairId"],
                tenor=row["tenor"],
                expiry=None,
                expiry_days=row["expiry_days"],
                strike=None,
                call_put=row["call_put"],
                delta=row["delta"],
                spot=row["spot_rate"],
                depo_base=0,
                depo_quote=0,
                bid_vol=row["Bid"] if "Bid" in row else None,
                ask_vol=row["Ask"] if "Ask" in row else None,
                mid_vol=row["Close"],
                bid_price=None,
                ask_price=None,
                mid_price=None,
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row['FxPairId'] > 0
        ]

    def get_insert_only_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'pair_id',
            'tenor',
            'expiry',
            'expiry_days',
            'strike',
            'call_put',
            'delta',
            'spot',
            'depo_base',
            'depo_quote',
            'bid_vol',
            'ask_vol',
            'mid_vol',
            'bid_price',
            'ask_price',
            'mid_price',
            'data_cut_id'
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "pair_id",
            "tenor",
            "call_put",
            "delta"
        ]

    def transform_data(self) -> pd.DataFrame:
        option_delta_regrex = "(A|10|25|45|10|25|45|10)"
        option_call_put_regrex = "(A|P|C|BF|RR|R|B)"
        # rename
        name_map = {'O=R': 'A', 'O=': 'A'}
        for key, val in name_map.items():
            self.df["name"] = self.df["name"].str.replace(key, val, regex=True)

        # extract delta and call_put
        self.df["delta"] = self.df["name"].str.extract(option_delta_regrex)  # offset
        self.df["delta"] = self.df["delta"].apply(lambda x: 0 if x == "A" else x).astype("float64")
        self.df["call_put"] = self.df["name"].str.extract(option_call_put_regrex)  # strategy
        # filter out unecessary elements
        self.df = self.df.loc[self.df['call_put'].isin(["A", "P", "C"])]
        self.df.drop_duplicates(subset=["date", "FxPair", "tenor", "name"], keep="first", inplace=True)
        return self.df

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str) -> pd.DataFrame:
        filt = (self.df['FxPair'] == pair) & (self.df['call_put'].isin(["A", "P", "C"]))
        df_inv_pair = self.df.loc[filt].copy()
        df_inv_pair["call_put"] = df_inv_pair["call_put"].str.replace("C", "temp", regex=True)
        df_inv_pair["call_put"] = df_inv_pair["call_put"].str.replace("P", "C", regex=True)
        df_inv_pair["call_put"] = df_inv_pair["call_put"].str.replace("temp", "P", regex=True)

        df_inv_pair["FxPair"] = inv_pair
        df_inv_pair["FxPairId"] = self.fx_pair_id_map[inv_pair]
        df_new = pd.concat([df_new, df_inv_pair], axis=0)
        return df_new

    def rename_column(self):
        self.df.rename(columns={"Universal Close Price": "Close",
                                "Reference Company": "Instrument ID"}, inplace=True)
