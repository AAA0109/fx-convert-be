from abc import ABC
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from hdlib.DateTime.Date import Date
import pytz
from django.db import models

from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.base import IbkrHtmlHandler
from main.apps.hedge.models import CurrencyMargin


class IbkrCurrencyMarginHandler(IbkrHtmlHandler, ABC):
    model: CurrencyMargin

    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        tables = pd.read_html(self.url)
        self.df = tables[0]
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
        rate_regex = r"(?P<rate>[0-9.]+)%\s+\(BM\s+[\+\-]\s+(?P<spread>[0-9\.]+)%\).*"
        rate_df = self.df['Rate Charged: IBKR Pro'].str.extractall(rate_regex).reset_index().drop(
            columns=['level_0', 'match'])
        rate_df['rate'] = rate_df['rate'].astype(float).div(100).round(5)
        rate_df['spread'] = rate_df['spread'].astype(float).div(100).round(5)
        self.df[['rate', 'spread']] = rate_df
        self.df['broker_id'] = self.broker.id
        self.df = self.df.replace({np.nan: None})
        self.df["_index"] = self.df["date"]
        self.df.set_index("_index", inplace=True)

    def create_models_with_df(self) -> Sequence[CurrencyMargin]:
        return [
            self.model(
                date=row['date'],
                broker_id=row['broker_id'],
                currency_id=row['currency_id'],
                tier_from=row['tier_from'],
                tier_to=row['tier_to'],
                rate=row['rate'],
                spread=row['spread']
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
