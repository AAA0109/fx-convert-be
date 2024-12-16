from datetime import datetime
import numpy as np
import pandas as pd

from abc import ABC
from typing import Optional, Sequence

from main.apps.dataprovider.services.importer.provider_handler.ibkr.csv.base import IbkrCsvHandler
from main.apps.ibkr.models import FutureContract


class IbkrFutureContractHandler(IbkrCsvHandler, ABC):
    model: FutureContract

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
    
    def create_models_with_df(self) -> Sequence[FutureContract]:
        return [
            self.model(
                base = row['ib_base'],
                con_id = row['ib_conid'],
                currency = row['ib_ccy'],
                description = row['ib_desc'],
                exchange = row['ib_exch'],
                fut_base = row['base'],
                fut_cont_size = row['fut_cont_size'],
                fut_month = row['ib_month'],
                fut_month_symbol = row['month'],
                fut_start_dt = self.__str_to_date(row['fut_start_dt']),
                fut_symbol = row['symbol'],
                fut_val_pt = row['fut_val_pt'],
                fut_year = row['year'],
                last_dt = self.__str_to_date(row['ib_lastdt']),
                lcode_long = row['lcode_long'],
                liquid_hours = row['ib_liquid_hours'],
                local_symbol = row['ib_locsym'],
                market_name = row['ib_name'],
                min_tick = row['ib_mintick'],
                multiplier = row['ib_mult'],
                price_magnifier = row['ib_pricemag'],
                roll_dt = self.__str_to_date(row['roll_dt']),
                sec_type = row['ib_type'],
                symbol = row['ib_symbol'],
                timezone_id = row['ib_timezone'],
                trading_hours = row['ib_trading_hours']
            )
            for index, row in self.df.iterrows()
        ]
    
    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return ['fut_symbol']
    
    def __str_to_date(self, date_str: str):
        return datetime.strptime(date_str, "%Y-%m-%d").date() if date_str != None else None
