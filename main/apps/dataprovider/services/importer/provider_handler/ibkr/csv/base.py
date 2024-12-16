from abc import ABC

import pandas as pd
from django.db import models
from main.apps.dataprovider.services.importer.provider_handler.handlers.csv import CsvHandler
from main.apps.marketdata.models.marketdata import DataCut


class IbkrCsvHandler(CsvHandler, ABC):
    
    def __init__(self, df: pd.DataFrame, data_provider_mappings: dict, profile_mappings: dict, data_cut_type: DataCut.CutType, model: models.Model):
        super().__init__(df, data_provider_mappings, profile_mappings, data_cut_type, model)