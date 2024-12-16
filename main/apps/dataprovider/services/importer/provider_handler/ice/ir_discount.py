import logging
from typing import Optional, Sequence, List

import pandas as pd
from hdlib.DateTime.Date import Date

from main.apps.dataprovider.services.importer.provider_handler.ice.base import IceHandler
from main.apps.marketdata.models.ir.discount import IrDiscount

logger = logging.getLogger(__name__)

 
class IceIrDiscountHandler(IceHandler):
    model: IrDiscount

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        currency_id_map = self._get_currency_id_map()
        self.splitted_sd_key.drop(columns=[0, 1, 3, 4, 5], inplace=True)
        self.splitted_sd_key.columns = ["FX", "tenor"]
        self.df = pd.concat([self.df, self.splitted_sd_key], axis=1)
        self.df["CurrencyId"] = self.df["Currency"].replace(currency_id_map).fillna(-1).astype(int)
        self.df["maturity"] = pd.to_datetime(self.df["Date"], format="%Y%m%d").apply(
            lambda x: x.tz_localize(self.tz))
        return self.df

    def create_models_with_df(self) -> Sequence[IrDiscount]:
        return [
            self.model(
                date=row["date"],
                currency_id=row["CurrencyId"],
                maturity=row["maturity"],
                maturity_days=-1,
                curve_id=row["Index"],
                discount=row["DF"] if 'DF' in row else None,
                data_cut_id=row["DataCutId"]
            )
            for index, row in self.df.iterrows() if row["CurrencyId"] > 0
        ]

    def handle_updated_models(self, updated_models: List):
        """ We need to loop through records after """
        if not updated_models:
            return

        for record in updated_models:
            day_counter = record.curve.make_day_counter()
            maturity_days = day_counter.days_between(Date.from_datetime(record.date),
                                                     Date.from_datetime_date(record.maturity))
            record.maturity_days = maturity_days
            if record.discount is None:
                # TODO: Need to add in logic to calculate discount factor if it's not in the CSV
                pass

        return updated_models

    def get_return_models(self) -> bool:
        return True

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
