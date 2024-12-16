from typing import Optional, Sequence

import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler.ice.cm_instrument import IceCmInstrumentHandler
from main.apps.marketdata.models.cm.future import CmInstrumentData


class IceCmInstrumentDataHandler(IceCmInstrumentHandler):
    model: CmInstrumentData

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df["instrument_id"] = self.df.apply(self._get_instrument_id, axis=1)
        return self.df
 
    def create_models_with_df(self) -> list:
        return [
            self.model(
                date=index,
                mid_price=None,
                bid_price=None,
                ask_price=row["Price"],
                asset_id=row["asset_id"],
                instrument_id=row["instrument_id"],
                data_cut_id=row["DataCutId"]
            )

            for index, row in self.df.iterrows() if row["asset_id"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "asset_id",
            "instrument_id"
        ]
