from abc import ABC

from django.db import models

from main.apps.broker.models import Broker
from main.apps.dataprovider.services.importer.provider_handler.handlers.html import HtmlHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.mixin.ibkr import IbkrProviderHandlerMixin
from main.apps.marketdata.models import DataCut


class IbkrHtmlHandler(HtmlHandler, IbkrProviderHandlerMixin, ABC):
    url: str
    broker: Broker

    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model, url: str, broker: Broker):
        super().__init__(data_cut_type=data_cut_type, model=model)
        self.url = url
        self.broker = broker

