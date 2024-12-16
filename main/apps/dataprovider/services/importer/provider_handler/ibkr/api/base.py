from abc import ABC
import logging
from typing import Dict

from django.db import models
from ib_insync import IB

from main.apps.dataprovider.services.connector.ibkr.api.tws import TwsApi
from main.apps.dataprovider.services.importer.provider_handler.handlers.api import ApiHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.mixin.ibkr import IbkrProviderHandlerMixin
from main.apps.ibkr.models import SupportedFxPair
from main.apps.marketdata.models import DataCut

logger = logging.getLogger(__name__)


class IbkrApiHandler(ApiHandler, IbkrProviderHandlerMixin, ABC):
    api: TwsApi
    client: IB

    def __init__(self, data_cut_type: DataCut.CutType, model: models.Model):
        super().__init__(data_cut_type=data_cut_type, model=model)
        self.api = TwsApi()
        try:
            self.client = self.api.get_client()
        except Exception as e:
            # TODO: use pub/sub to publish event
            self.client = None
            logger.error(str(e))

    def execute(self):
        if self.client:
            super().execute()
            self.client.disconnect()

    @staticmethod
    def _get_fx_pair_id_map() -> Dict[str, int]:
        fx_pairs = SupportedFxPair.get_ibkr_supported_pairs()
        mappings = {}
        for fx_pair in fx_pairs:
            mappings[fx_pair.base_currency.mnemonic + fx_pair.quote_currency.mnemonic] = fx_pair.id
        return mappings
