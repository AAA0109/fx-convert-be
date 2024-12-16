import numpy as np
import pandas as pd

from typing import Optional, Sequence

from main.apps.dataprovider.services.importer.provider_handler.fincal.csv.base import FincalCsvHandler
from main.apps.marketdata.models.fincal.tradingcalendar import TradingCalendarFincal

 
class TradingCalendarHandler(FincalCsvHandler):
    DATE_TIME_FORMAT = "%Y%m%d %H:%M:%S"
    DATE_FORMAT = "%Y%m%d"

    def add_data_cut_to_df(self):
        pass

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df = self.df.replace(r'^\s*$', np.nan, regex=True)
        self.df = self.df.replace({np.nan: None})
        return self.df

    def transform_data(self) -> pd.DataFrame:
        self.df = self.df.rename(columns=str.lower)

        for column in ['trade_date', 'locl_open', 'locl_close', 'nyus_open', 'nyus_close', 'gmtt_open', 'gmtt_close']:
            self.df[column] = self.df[column].astype(str)
            self.df[column] = self.df[column].str.replace('/', '')

            # Sometime date column other than trade_date only consist of date part
            # So we need to add the time part. In this case with 00:00:00
            if column != 'trade_date':
                self.df[column] = self.df[column].apply(lambda x: self.add_time_part(x))

            if column == 'gmtt_open' or column == 'gmtt_close':
                self.df[column] = pd.to_datetime(self.df[column], format=self.DATE_TIME_FORMAT, utc=True)
            elif column == 'trade_date':
                self.df[column] = pd.to_datetime(self.df[column], format=self.DATE_FORMAT)
                self.df[column] = self.df[column].dt.date
            else:
                self.df[column] = pd.to_datetime(self.df[column], format=self.DATE_TIME_FORMAT)
        return self.df

    def create_models_with_df(self) -> Sequence[TradingCalendarFincal]:
        rows = []
        for index, row in self.df.iterrows():
            rows.append(self.model(
                trade_date = row['trade_date'],
                cen_code = row['cen_code'],
                market = row['market'],
                irregular = row['irregular'],
                irreg_sess = row['irreg_sess'],
                new_hours = row['new_hours'],
                functions = row['functions'],
                activity = row['activity'],
                local_open = row['locl_open'],
                local_close = row['locl_close'],
                first_open = row['frst_open'],
                last_open = row['last_open'],
                first_close = row['frst_close'],
                last_close = row['last_close'],
                nyus_open = row['nyus_open'],
                nyus_close = row['nyus_close'],
                gmtt_open = row['gmtt_open'],
                gmtt_close = row['gmtt_close'],
                gmtoff_op = row['gmtoff_op'] if 'gmtoff_op' in self.df.columns else None,
                fmtoff_cl = row['fmtoff_cl'] if 'fmtoff_cl' in self.df.columns else None,
            ))
        return rows

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return ['cen_code', 'gmtt_open', 'gmtt_close']

    def add_time_part(self, value: str) -> str:
        if not value or value == 'None':
            return None

        splits = value.split(' ')
        if len(splits) == 1:
            return f"{value} 00:00:00"
        return value
