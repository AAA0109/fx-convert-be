from abc import ABC, abstractmethod
from typing import Optional, Type

import pandas as pd
from django.db import models

from main.apps.currency.models import FxPair
from main.apps.dataprovider.services.importer.provider_handler.handler import Handler
from main.apps.marketdata.models import DataCut


class ApiHandler(Handler, ABC):
    data_cut_type: DataCut.CutType
    model: Type[models.Model]
    """
    Base api handler class, used for downloading data from an API and importing it directly to
    database tables.
    """
    df: pd.DataFrame = None
    fx_pair_id_map: dict

    def __init__(self, data_cut_type: DataCut.CutType, model: Type[models.Model]):
        super().__init__(data_cut_type=data_cut_type)
        self.model = model

    def execute(self):
        """ Data importer entry point function, this method is invoked for each Profile"""
        self.get_data_from_api()

        if isinstance(self.df, pd.DataFrame) and not self.df.empty:
            self.before_handle()
            self.clean_data()
            self.transform_data()
            self.handle()
            self.after_handle()

    @abstractmethod
    def get_data_from_api(self) -> Optional[pd.DataFrame]:
        """ This method must be implemented, it should pull the data from the provider and setup self.df for
        database insertion"""
        raise NotImplementedError

    def create_reverse_pairs(self):
        unique_fx_pair_id = self.df["FxPairId"].unique()
        df_new = pd.DataFrame(columns=self.df.columns)
        for fx_pair_id in unique_fx_pair_id:
            if fx_pair_id < 0:
                continue
            df_new = self.create_reverse_pair(df_new, fx_pair_id, unique_fx_pair_id)
        self.df = pd.concat([self.df, df_new], axis=0)

    def create_reverse_pair(self, df_new: pd.DataFrame, fx_pair_id: int, unique_fx_pair_id: int):
        fx_pair = FxPair.objects.get(pk=fx_pair_id)
        if not FxPair.objects.filter(base_currency=fx_pair.quote_currency, quote_currency=fx_pair.base_currency):
            raise RuntimeError(f"we need to add fx pair {fx_pair.inverse_name}")

        pair = FxPair.objects.get(pk=fx_pair_id).name.replace("/", "")
        inv_pair = FxPair.objects.get(pk=fx_pair_id).inverse_name.replace("/", "")
        if self.fx_pair_id_map[inv_pair] not in unique_fx_pair_id:
            df_new = self.calculate_reverse_values(df_new, pair, inv_pair)
        return df_new

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair: str, inv_pair: str):
        return df_new
