from typing import Optional, Sequence

import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models.cm.future import CmInstrument


class IceCmInstrumentHandler(IceHandler):
    model: CmInstrument

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df.dropna(subset=["AssetName", "Unit", "Currency", "Contract", "Expiry", "Price"], thresh=3, inplace=True)
        self.df["CurrencyId"] = self.df["Currency"].replace(self._get_currency_id_map()).fillna(-1).astype(int)
        self.df["AssetName"] = self.df["AssetName"].str.extract("(Gold|Silver)")
        self.df["asset_id"] = self.df.apply(self._get_asset_id, axis=1)
        self.df["Expiry"] = pd.to_datetime(self.df["Expiry"], format='%Y-%m-%f').apply(lambda x: x.tz_localize(self.tz))
        return self.df
 
    def create_models_with_df(self) -> list:
        return [
            self.model(
                expiry=row["Expiry"],
                expiry_label=row["Contract"],
                asset_id=row["asset_id"]
            )
            for index, row in self.df.iterrows() if row["asset_id"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "expiry_label",
            "asset_id"
        ]
    def enable_fxpair_extraction(self) -> bool:
        return False