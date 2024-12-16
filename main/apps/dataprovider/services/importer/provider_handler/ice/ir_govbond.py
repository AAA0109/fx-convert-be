import logging
from typing import Optional, Sequence, List

import pandas as pd
from hdlib.DateTime.Date import Date

from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models.ir.discount import IrCurve
from main.apps.marketdata.models.ir.govbond import GovBond

logger = logging.getLogger(__name__)
 

class IceGovBondHandler(IceHandler):
    model: GovBond

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        issuer_id_map = self._get_issuer_id_map()
        currency_id_map = self._get_currency_id_map()
        self.df["Issuer"] = self.df["Issuer"].str.lower()
        self.df["IssuerId"] = self.df["Issuer"].replace(issuer_id_map).fillna(-1).astype(int)
        self.df["CurrencyId"] = self.df["Currency"].replace(currency_id_map).fillna(-1).astype(int)
        self.df["maturity"] = pd.to_datetime(self.df["MaturityDate"], format="%Y-%m-%d").apply(lambda x: x.tz_localize(self.tz))
        self.df["maturity_days"] = (self.df["maturity"]  - self.df.index).dt.days
        return self.df

    def create_models_with_df(self) -> Sequence[GovBond]:
        return [
            self.model(
                date=row["date"],
                issuer_id=row["IssuerId"],
                currency_id=row["CurrencyId"],
                tenor=row["Tenor"],
                maturity=row["maturity"],
                maturity_days=row["maturity_days"],
                ytm=row["Yield"] if row["Yield"] is not None else 0, # todo: make sure this!
                price=row["Price"],
                coupon=row["Coupon"],
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["CurrencyId"] > 0
        ]


    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "issuer_id",
            "currency_id",
            "tenor",
            "maturity"
        ]

    def get_update_update_field_names(self) -> Optional[Sequence[str]]:
        return [
            "date",
            "issuer_id",
            "currency_id",
            "tenor",
            "maturity",
            "maturity_days",
            "ytm",
            "price",
            "coupon",
            "data_cut_id"
        ]
