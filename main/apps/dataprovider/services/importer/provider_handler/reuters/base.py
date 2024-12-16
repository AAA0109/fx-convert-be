from abc import ABC
from re import Pattern
from typing import Dict, Union

import pandas as pd

from main.apps.currency.models.fxpair import FxPair
from main.apps.dataprovider.services.importer.provider_handler.handlers.csv import CsvHandler

 
class ReutersHandler(CsvHandler, ABC):
    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.rename_column()
        self.df = self._set_date_as_index(self.df.copy())
        self.fx_pair_regex = self._get_fx_pair_regex()
        self.fx_pair_id_map = self._get_fx_pair_id_map()
        self.fx_pair_map=self.get_fx_pair_map()
        if self.fx_pair_regex:
            if "Instrument ID" in self.df.columns:
                self.df["Currency"] = self.df["Instrument ID"].str.extract(self.fx_pair_regex)
            if "RIC" in self.df.columns:
                self.df["Currency"] = self.df["RIC"].str.extract(self.fx_pair_regex)
            self.df["FxPair"] = self.df["Currency"].replace(to_replace=self.fx_pair_map)
            self.df["FxPairId"] = self.df["FxPair"].replace(self.fx_pair_id_map).fillna(-1).replace('', -1).astype(int)
        return self.df

    @staticmethod
    def _get_fx_pair_regex() -> Union[str,bool]:
        fx_pairs = list(FxPair.get_pairs_by_base_quote_currency())
        if not len(fx_pairs):
            return False
        regex = "("
        for fx_pair in fx_pairs:
            if fx_pair.base_currency.mnemonic != 'USD':
                mnemonic = fx_pair.base_currency.mnemonic
                regex += mnemonic
            if fx_pair.quote_currency.mnemonic != 'USD':
                mnemonic = fx_pair.quote_currency.mnemonic
                regex += mnemonic
            if not fx_pair == fx_pairs[-1]:
                regex += '|'
        regex += ")"
        return regex

    def get_fx_pair_map(self):
        '''
        reuter only provide single currency code as a representation of currency pair
        '''
        return {"EUR": "EURUSD",
                "GBP": "GBPUSD",
                "CAD": "USDCAD",
                "MXN": "USDMXN",
                "JPY": "USDJPY",
                "AUD": "AUDUSD",
                "CNY": "USDCNY",
                "TRY": "USDTRY",
                "KRW": "USDKRW",
                "SGD": "USDSGD",
                "ZAR": "USDZAR",
                "IDR": "USDIDR",
                "INR": "USDINR",
                "CHF": "USDCHF",
                "BRL": "USDBRL",
                "RUB": "USDRUB",
                "ANG": "USDANG",
                "SAR": "USDSAR",
                "ARS": "USDARS"}

    @staticmethod
    def _get_fx_pair_id_map() -> Dict[str, int]:
        fx_pairs = FxPair.get_pairs_by_base_quote_currency()
        mappings = {}
        for fx_pair in fx_pairs:
            mappings[fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic] = fx_pair.id
        return mappings

    def rename_column(self):
        pass
