from abc import ABC

import pandas as pd
from django.db import models
from main.apps.dataprovider.services.importer.provider_handler.handlers.xlsx import XlsxHandler
from main.apps.marketdata.models.marketdata import DataCut


class CorpayXlsxHandler(XlsxHandler, ABC):
    def __init__(self, df: pd.DataFrame, fpath: str, data_cut_type: DataCut.CutType, model: models.Model):
        super().__init__(df, fpath, data_cut_type, model)



