import logging
from typing import Optional, Sequence, List

import pandas as pd
from hdlib.DateTime.Date import Date

from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models.ir.discount import IBORRate
from main.apps.marketdata.models.ir.discount import IrCurve

logger = logging.getLogger(__name__)


class IceIBORRateHandler(IceHandler):
    model: IBORRate
 
    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        currency_id_map = self._get_currency_id_map()
        self.df["Currency"] = self.splitted_sd_key.loc[:, 2]
        self.df["Family"] = self.splitted_sd_key.loc[:, 4]
        self.df["Name"] = self.splitted_sd_key.loc[:, 3]
        self.df["CurrencyId"] = self.df["Currency"].replace(currency_id_map).fillna(-1).astype(int)
        self.df["curve_id"] = self.df.apply(self._get_curve_id, axis=1)
        self.df = pd.concat([self.df, self.splitted_sd_key], axis=1)
        self.df["maturity"] = pd.to_datetime(self.df["Date"], format="%Y%m%d").apply(
            lambda x: x.tz_localize(self.tz))
        self.df["maturity_days"] = (self.df["maturity"] - self.df.index).dt.days

        return self.df

    def create_models_with_df(self) -> Sequence[IBORRate]:
        return [
            self.model(
                date=row["date"],
                currency_id=row["CurrencyId"],
                maturity=row["Instrument"],

            )
            for index, row in self.df.iterrows() if row["CurrencyId"] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "currency_id",
            "maturity"
        ]

    def get_update_update_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "maturity",
            "maturity_days",
            "discount",
            "currency_id",
            "curve_id",
            "data_cut_id"
        ]
