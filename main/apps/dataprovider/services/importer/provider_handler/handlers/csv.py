from abc import ABC
import pandas as pd
import logging

from django.db import models

from main.apps.currency.models import FxPair
from main.apps.dataprovider.services.importer.provider_handler.handler import Handler
from main.apps.marketdata.models.marketdata import DataCut

logger = logging.getLogger(__name__)


class CsvHandler(Handler, ABC):
    """
    Base csv handler class, used for processing raw data and import into proper database tables.
    Different data providers (and/or data formats) will require their own handlers
    """ 
    df: pd.DataFrame = None
    data_provider_mappings: dict = {}
    profile_mappings: dict = {}
    created_records: []
    data_cut_type: DataCut.CutType = None
    model: models.Model = None
    fx_pair_regex: str
    fx_pair_map: dict
    fx_pair_id_map: dict

    def __init__(self, df: pd.DataFrame, data_provider_mappings: dict, profile_mappings: dict,
                 data_cut_type: DataCut.CutType, model: models.Model):
        self.df = df
        self.data_provider_mappings = data_provider_mappings
        self.profile_mappings = profile_mappings
        self.data_cut_type = data_cut_type
        self.model = model

    def execute(self):
        """ Data importer entry point function, this method is invoked for each Profile"""
        self.before_handle()
        self.replace_data_with_mappings()
        self.transform_data()
        self.clean_data()
        self.handle()
        self.after_handle()

    def replace_data(self, mappings: dict) -> pd.DataFrame:
        """ Replaces DataFrame column values with mappings dictionary"""
        for column_name, column_maps in mappings.items():
            for col_map in column_maps:
                if not column_name:
                    self.df.replace(col_map)
                else:
                    self.df = self.df.replace({column_name: col_map})
        return self.df

    def replace_data_with_mappings(self):
        """ This function uses the Data Provider and Profile Mappings to replaces mapped values"""
        if len(self.data_provider_mappings):
            self.df = self.replace_data(self.data_provider_mappings)
        if len(self.profile_mappings):
            self.df = self.replace_data(self.profile_mappings)
        return self.df

    def create_reverse_pairs(self):
        unique_fx_pair_id = self.df["FxPairId"].unique()
        df_new = pd.DataFrame(columns=self.df.columns)
        for fx_pair_id in unique_fx_pair_id:
            if fx_pair_id < 0:
                continue;
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

    def calculate_reverse_values(self, df_new: pd.DataFrame, pair:FxPair, inv_pair:FxPair):
        return df_new

    @staticmethod
    def _set_date_as_index(df):
        df['date_index'] = df['date']
        return df.set_index("date_index")
