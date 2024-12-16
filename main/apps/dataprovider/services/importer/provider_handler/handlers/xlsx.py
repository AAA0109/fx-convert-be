from abc import ABC
import pandas as pd

from django.db import models

from main.apps.dataprovider.services.importer.provider_handler.handler import Handler
from main.apps.marketdata.models.marketdata import DataCut


class XlsxHandler(Handler, ABC):
    """
    Base xlsx handler class, used for processing raw data and import into proper database tables.
    Different data providers (and/or data formats) will require their own handlers
    """
    df: pd.DataFrame = None
    data_cut_type: DataCut.CutType = None
    model: models.Model = None
 
    def __init__(self, df: pd.DataFrame, fpath: str, data_cut_type: DataCut.CutType,  model: models.Model):
        self.df = df
        self.fpath = fpath
        self.data_cut_type = data_cut_type
        self.model = model

    def execute(self):
        """ Data importer entry point function, this method is invoked for each Profile"""
        self.before_handle()
        self.transform_data()
        self.clean_data()
        self.handle()
        self.after_handle()

    def add_data_cut_to_df(self):
        pass
