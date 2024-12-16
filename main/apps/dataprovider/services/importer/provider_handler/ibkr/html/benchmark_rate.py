import logging
from abc import ABC
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import pytz
from hdlib.DateTime.Date import Date

from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.base import IbkrHtmlHandler
from main.apps.hedge.models import BenchmarkRate

logger = logging.getLogger(__name__)


class IbkrBenchmarkRateHandler(IbkrHtmlHandler, ABC):
    model: BenchmarkRate

    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        try:
            tables = pd.read_html(self.url)
            if tables.empty:
                logger.error(f"No tables found in the URL: {self.url}")
            self.df = tables[0]
            return self.df
        except Exception as e:
            raise Exception(f"Error occurred while reading HTML from URL: {self.url}. Error: {str(e)}")

    def clean_data(self) -> pd.DataFrame:
        self.df.drop(self.df.tail(1).index, inplace=True)
        if 'Unnamed: 4' in self.df.columns:
            self.df.drop(columns=['Unnamed: 4'], inplace=True)
        self.df.columns = self.df.columns.str.replace(r"Description.*", "description")
        return self.df

    def transform_data(self):
        now = Date.now()
        tz = pytz.timezone('US/Eastern')
        date = Date(now.year, now.month, now.day, 17, 0, 0)
        date = tz.localize(date)
        self.df['date'] = date
        currency_map = self._get_currency_id_map()
        self.df['currency_id'] = self.df['Currency'].map(currency_map).fillna(-1).astype(int)
        rate_regex = r"(?P<rate>[()0-9.]+)%"
        rate_df = self.df['Rate'].str.extractall(rate_regex).reset_index().drop(
            columns=['level_0', 'match'])
        rate_df = rate_df.replace('[)]', '', regex=True).replace('[(]', '-', regex=True)
        rate_df['rate'] = rate_df['rate'].astype(float).div(100).round(5)
        self.df[['rate']] = rate_df
        self.df['broker_id'] = self.broker.id
        self.df = self.df.replace({np.nan: None})
        self.df['effective_date'] = pd.to_datetime(self.df['Effective Date'], utc=True)
        self.df["_index"] = self.df["date"]
        self.df.set_index("_index", inplace=True)

    def create_models_with_df(self) -> Sequence[BenchmarkRate]:
        return [
            self.model(
                broker_id=row['broker_id'],
                currency_id=row['currency_id'],
                description=row['description'],
                rate=row['rate'],
                effective_date=row['effective_date']
            )
            for index, row in self.df.iterrows() if row['currency_id'] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'broker_id',
            'currency_id',
            'effective_date'
        ]
