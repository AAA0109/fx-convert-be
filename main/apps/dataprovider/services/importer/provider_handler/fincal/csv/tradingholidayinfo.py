import numpy as np
import pandas as pd

from typing import Optional, Sequence

from main.apps.dataprovider.services.importer.provider_handler.fincal.csv.base import FincalCsvHandler
from main.apps.marketdata.models.fincal.tradingholidays import TradingHolidaysInfoFincal
 

class TradingHolidaysInfoHandler(FincalCsvHandler):
    def add_data_cut_to_df(self):
        pass

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df = self.df.replace(r'^\s*$', np.nan, regex=True)
        self.df = self.df.replace({np.nan:None})
        return self.df

    def transform_data(self) -> pd.DataFrame:
        self.df = self.df.rename(columns=str.lower)
        return self.df

    def create_models_with_df(self) -> Sequence[TradingHolidaysInfoFincal]:
        rows = []
        for index, row in self.df.iterrows():
            rows.append(self.model(
                code = row['code'],
                center = row['center'],
                country = row['country'],
                currency = row['currency'],
                info_type = row['type'],
                iso_country = row['isocountry'],
                define_1 = row['define1'],
                define_2 = row['define2']
            ))
        return rows

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return ['code']
