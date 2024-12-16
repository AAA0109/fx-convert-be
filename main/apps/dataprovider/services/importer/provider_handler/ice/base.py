from abc import ABC
from re import Pattern
from typing import Union

import pandas as pd

from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.dataprovider.services.importer.provider_handler.handlers.csv import CsvHandler
from main.apps.marketdata.models.cm import CmAsset
from main.apps.marketdata.models.cm.future import CmInstrument
from main.apps.marketdata.models.ir.discount import IrCurve
from main.apps.marketdata.models.ir.govbond import Issuer


class IceHandler(CsvHandler, ABC):
    splitted_sd_key: pd.DataFrame

    def before_handle(self) -> pd.DataFrame:
        super().before_handle()
        self.df = self.df[self.df['Status'] != 'Failed']
        self.fx_pair_regex = self._get_fx_pair_regex()
        self.fx_pair_id_map = self._get_fx_pair_id_map()
        self.tz = str(self.df["date"].dt.tz)
        self.df = self._set_date_as_index(self.df.copy())
        if self.fx_pair_regex and "SDKey" in self.df.columns and self.enable_fxpair_extraction():
            self.df["FxPair"] = self.df["SDKey"].str.extract(self.fx_pair_regex)
            self.df["FxPairId"] = self.df["FxPair"].replace(self.fx_pair_id_map).fillna(-1).astype(int)
            self.splitted_sd_key = self.df["SDKey"].str.split(r"_", expand=True)
        return self.df

    @staticmethod
    def _get_fx_pair_regex() -> Union[str, bool]:
        fx_pairs = list(FxPair.get_pairs_by_base_quote_currency())
        if not len(fx_pairs):
            return False
        regex = "("
        for fx_pair in fx_pairs:
            regex += fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic
            if not fx_pair == fx_pairs[-1]:
                regex += '|'
        regex += ")"
        return regex

    @staticmethod
    def _get_fx_pair_id_map() -> dict:
        fx_pairs = FxPair.get_pairs_by_base_quote_currency()
        mappings = {}
        for fx_pair in fx_pairs:
            mappings[fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic] = fx_pair.id
        return mappings

    @staticmethod
    def _get_asset_id(series: pd.Series) -> int:
        return CmAsset.objects.get(name=series["AssetName"], units=series["Unit"], currency_id=series["CurrencyId"]).id

    @staticmethod
    def _get_instrument_id(series: pd.Series) -> int:
        return CmInstrument.objects.get(expiry_label=series["Contract"], asset_id=series["asset_id"]).id

    @staticmethod
    def _get_issuer_id_map():
        issuers = Issuer.objects.all()
        mappings = {}
        for issuer in issuers:
            mappings[issuer.name.lower()] = issuer.id
        return mappings

    @staticmethod
    def _get_curve_id(series: pd.Series) -> int:
        return IrCurve.objects.get(currency_id=series["CurrencyId"], name=series["Name"]).id

    def enable_fxpair_extraction(self) -> bool:
        return True
