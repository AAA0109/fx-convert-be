import datetime
from abc import ABC
from typing import Optional, Sequence

import numpy as np
import pandas as pd
import pytz
from hdlib.DateTime.Date import Date
from django.db import models

from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.base import IbkrHtmlHandler
from main.apps.hedge.models import CurrencyMargin, InterestRate


class IbkrInterestRateHandler(IbkrHtmlHandler, ABC):
    model: InterestRate

    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        tables = pd.read_html(self.url)
        self.df = tables[1]
        return self.df

    def clean_data(self) -> pd.DataFrame:
        self.df.fillna(method="ffill", inplace=True)
        return self.df

    def transform_data(self):
        now = Date.now()
        tz = pytz.timezone('US/Eastern')
        date = Date(now.year, now.month, now.day, 17, 0, 0)
        date = tz.localize(date)
        self.df['date'] = date
        currency_map = self._get_currency_id_map()
        self.df['currency_id'] = self.df['Currency'].map(currency_map).fillna(-1).astype(int)
        tier_regex = r"((?P<tier_from>[0-9]+)?\s?(?P<tier_condition>[≤>])\s?(?P<tier_to>[0-9]+)|(?P<is_all>All))"
        tier_df = self.df["Tier"].str.replace(",", "").str.extractall(tier_regex).reset_index().drop(
            columns=[0, 'level_0', 'match', 'is_all'])
        tier_df.loc[tier_df['tier_from'].isna(), ['tier_from', 'tier_to']] = tier_df.loc[
            tier_df['tier_from'].isna(), ['tier_to', 'tier_from']].values
        self.df[['tier_from', 'tier_condition', 'tier_to']] = tier_df
        rate_regex = r"(?P<rate_paid>[0-9.]+)%(\s+\(BM\s+[\+\-]\s+(?P<spread>[0-9\.]+)%\).*)?"
        rate_df = self.df['Rate Paid:  IBKR Pro'].str.extractall(rate_regex).reset_index().drop(
            columns=['level_0', 'match'])
        rate_df['rate_paid'] = rate_df['rate_paid'].astype(float).div(100).round(5)
        rate_df['spread'] = rate_df['spread'].astype(float).div(100).round(5)
        self.df[['rate_paid', 'spread']] = rate_df[['rate_paid', 'spread']]
        self.df['broker_id'] = self.broker.id
        self.df = self.df.replace({np.nan: None})
        self.df["_index"] = self.df["date"]
        self.df.set_index("_index", inplace=True)

    def create_models_with_df(self) -> Sequence[InterestRate]:
        return [
            self.model(
                broker_id=row['broker_id'],
                currency_id=row['currency_id'],
                tier_from=row['tier_from'],
                tier_to=row['tier_to'],
                rate=row['rate_paid'],
                spread=row['spread'],
                date=index
            )
            for index, row in self.df.iterrows() if row['currency_id'] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'date',
            'broker_id',
            'currency_id',
            'tier_from',
            'tier_to'
        ]
