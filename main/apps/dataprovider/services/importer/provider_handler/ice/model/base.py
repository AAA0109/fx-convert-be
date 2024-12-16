from abc import ABC

from django.db import models

from main.apps.dataprovider.services.importer.provider_handler.handlers.model import ModelHandler
from main.apps.marketdata.models import DataCut


class IceModelHandler(ModelHandler, ABC):

    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model):
        super().__init__(data_cut_type=data_cut_type, model=model)
