import pytz
from hdlib.DateTime.Date import Date
from abc import ABC
from typing import Optional, Sequence

import pandas as pd

from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.base import IbkrHtmlHandler
from main.apps.margin.models import FxSpotMargin


class IbkrFxSpotMarginHandler(IbkrHtmlHandler, ABC):
    model: FxSpotMargin

    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        tables = pd.read_html(self.url)
        self.df = tables[0]
        return self.df

    def transform_data(self):
        now = Date.now()
        tz = pytz.timezone('US/Eastern')
        date = Date(now.year, now.month, now.day, 17, 0, 0)
        date = tz.localize(date)
        self.df['date'] = date
        fx_pair_id_map = self._get_fx_pair_id_map()
        margin_regex = r"([0-9.]+)%\s\([0-9:.]+\)"
        initial_rate = self.df['Initial Margin'].str.extract(margin_regex)
        maintenance_rate = self.df['Maintenance Margin'].str.extract(margin_regex)
        nfa_rate = self.df["NFA Margin on Cash Forex Position Only 1"].str.extract(margin_regex)
        self.df['rate'] = initial_rate.astype(float).div(100).round(5)
        self.df['maintenance_rate'] = maintenance_rate.astype(float).div(100).round(5)
        self.df['nfa_rate'] = nfa_rate.astype(float).div(100).round(5)
        self.df['broker_id'] = self.broker.id
        df_new = self.df.copy(deep=True)
        df_new = self.df[self.df['Currency'] != 'USD']
        df_new['fx_pair'] = df_new['Currency'] + 'USD'
        self.df['fx_pair'] = 'USD' + self.df['Currency']
        self.df = pd.concat([self.df, df_new], axis=0)
        self.df['pair_id'] = self.df['fx_pair'].map(fx_pair_id_map).fillna(-1)
        self.df["_index"] = self.df["date"]
        self.df.set_index("_index", inplace=True)

    def create_models_with_df(self) -> Sequence[FxSpotMargin]:
        return [
            self.model(
                date=index,
                rate=row['rate'],
                broker_id=row['broker_id'],
                data_cut_id=row['DataCutId'],
                pair_id=row['pair_id'],
                maintenance_rate=row['maintenance_rate'],
                nfa_rate=row['nfa_rate']
            )
            for index, row in self.df.iterrows() if row['pair_id'] > 0
        ]

    def get_pk_field_names(self) -> Optional[Sequence[str]]:
        return [
            'data_cut_id',
            'pair_id',
            'broker_id'
        ]

    def _get_fx_pair_id_map(self):
        pairs = self.get_supported_pairs()
        mappings = {}
        for pair in pairs:
            mappings[pair.base_currency.mnemonic + pair.quote_currency.mnemonic] = pair.id
        return mappings
