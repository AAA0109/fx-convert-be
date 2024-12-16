import numpy as np
import pandas as pd

from typing import Optional, Sequence

from main.apps.dataprovider.services.importer.provider_handler.fincal.csv.base import FincalCsvHandler
from main.apps.marketdata.models.fincal.tradingholidays import TradingHolidaysCodeFincal

 
class TradingHolidaysCodeHandler(FincalCsvHandler):
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

    def create_models_with_df(self) -> Sequence[TradingHolidaysCodeFincal]:
        return [
            self.model(
                code = row['code'],
                holiday = row['holiday'],
            )
            for index, row in self.df.iterrows()
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return ['code', 'holiday']
