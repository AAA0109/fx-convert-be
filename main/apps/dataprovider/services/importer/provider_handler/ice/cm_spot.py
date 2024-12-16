import re
from typing import Optional, Sequence

import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models.cm.spot import CmSpot


class IceCmSpotHandler(IceHandler):
    model: CmSpot

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df['Currency'] = self.df['SDKey'].str.extract(self._get_currency_regex())
        self.df['CurrencyId'] = self.df['Currency'].replace(self._get_currency_id_map()).fillna(-1).astype(int)
        self.df['Unit'] = pd.Series(["oz","oz"],index=self.df.index)
        self.df['AssetName'] = self.df['SDKey'].str.extract("(XAU|XAG)").replace({"XAU":"Gold","XAG":"Silver"})
        self.df["asset_id"] = self.df.apply(self._get_asset_id, axis=1)
        return self.df
 
    def create_models_with_df(self) -> list:
        return [
            self.model(
                date=index,
                asset_id=row["asset_id"],
                mid_price=None,
                bid_price=None,
                ask_price=row["Mid"] if 'Mid' in row else None,
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["asset_id"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "asset_id"
        ]

    def enable_fxpair_extraction(self) -> bool:
        return False