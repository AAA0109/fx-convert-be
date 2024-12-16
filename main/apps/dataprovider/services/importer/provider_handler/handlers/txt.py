from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd
from django.db import models

from main.apps.dataprovider.services.importer.provider_handler.handler import Handler
from main.apps.marketdata.models import DataCut


class TxtHandler(Handler, ABC):
    data_cut_type: DataCut.CutType
    model: models.Model
    url: str
    """
    Base api handler class, used for downloading data from an API and importing it directly to
    database tables.
    """
    df: pd.DataFrame = None
 
    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model):
        self.data_cut_type = data_cut_type
        self.model = model

    def execute(self):
        """ Data importer entry point function, this method is invoked for each Profile"""
        self.get_data_from_url()
        self.before_handle()
        self.clean_data()
        self.transform_data()
        self.handle()
        self.after_handle()

    @abstractmethod
    def get_data_from_url(self) -> Optional[pd.DataFrame]:
        """ This method must be implemented, it should pull the data from the provider and setup self.df for
        database insertion"""
        raise NotImplementedError

    def add_data_cut_to_df(self):
        pass
