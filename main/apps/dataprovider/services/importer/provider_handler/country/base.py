from abc import ABC

from django.db import models

from main.apps.broker.models import Broker
from main.apps.dataprovider.services.importer.provider_handler.handlers.json import JsonHandler
from main.apps.dataprovider.services.importer.provider_handler.handlers.txt import TxtHandler
from main.apps.marketdata.models import DataCut


class CountryUrlTxtHandler(TxtHandler, ABC):
    url: str


    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model, url: str):
        super().__init__(data_cut_type=data_cut_type, model=model)
        self.url = url

class CountryJsonFileHandler(JsonHandler, ABC):
    url: str
    file_path: str

    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model, url: str, file_path:str):
        super().__init__(data_cut_type=data_cut_type, model=model)
        self.url = url
        self.file_path = file_path


