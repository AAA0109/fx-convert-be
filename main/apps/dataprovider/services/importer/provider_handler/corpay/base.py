import traceback
from abc import ABC
from datetime import datetime
import logging
from typing import Dict, List, Optional, Type

from django.db import models
from django.conf import settings
from main.apps.account.models.company import Company
from main.apps.core.models.config import Config

from main.apps.corpay.services.api.connector.auth import CorPayAPIAuthConnector
from main.apps.corpay.services.corpay import CorPayService
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.dataprovider.services.importer.provider_handler.handlers.api import ApiHandler
from main.apps.marketdata.models import DataCut
from main.apps.marketdata.models import CorpayFxSpot, CorpayFxForward
from main.apps.marketdata.services.data_cut_service import DataCutService

logger = logging.getLogger(__name__)


class CorPayHandler(ApiHandler, ABC):
    auth_api: CorPayAPIAuthConnector
    config_path: str
    datacut_eod_utc_hour_path = 'system/datacut/eod_utc_hour'
    datacut_benchmark_utc_hour_path = 'system/datacut/benchmark_utc_hour'
    eod_utc_hour: int
    benchmark_utc_hour: int

    def __init__(self, data_cut_type: DataCut.CutType, model: Type[models.Model]):
        self.auth_api = CorPayAPIAuthConnector()
        self.company = self.get_company_from_config_path()
        self.client_code = self.company.corpaysettings.client_code
        self.eod_utc_hour = Config.get_config(path=self.datacut_eod_utc_hour_path).value
        self.benchmark_utc_hour = Config.get_config(path=self.datacut_benchmark_utc_hour_path).value
        super().__init__(data_cut_type, model)

    def get_client_access_code(self):
        response = self.auth_api.partner_level_token_login()
        partner_access_code = response['access_code']
        response = self.auth_api.client_level_token_login(
            user_id=self.company.corpaysettings.user_id,
            client_level_signature=self.company.corpaysettings.signature,
            partner_access_code=partner_access_code
        )
        client_access_code = response['access_code']
        return client_access_code

    def get_company_access_code(self, company: Company) -> Optional[str]:
        try:
            corpay_service = CorPayService()
            corpay_service.init_company(company)
            client_access_code = corpay_service.get_client_access_code()
        except Exception as e:
            traceback.print_exc()
            client_access_code = None
            logger.error(f"Credential not exist for company {company.name}")
        return client_access_code

    def get_company_from_config_path(self) -> Company:
        config = Config.get_config(path=self.config_path)
        company_id = config.value
        company = Company.get_company(company=company_id)
        return company

    def populate_fxpairs(self, fxpair_id: Optional[str], used_currencies: List[Currency]) -> List[FxPair]:
        pairs: List[FxPair] = []
        if fxpair_id:
            pair = FxPair.get_pair(pair=fxpair_id)
            return [pair]
        else:
            for currency_base in used_currencies:
                for currency_quote in used_currencies:
                    if currency_base.mnemonic != currency_quote.mnemonic:
                        pair = FxPair.get_pair_from_currency(base_currency=currency_base, quote_currency=currency_quote)
                        if pair:
                            pairs.append(pair)
        return pairs

    def get_datacut(self, fxpair_id: Optional[int], date: datetime) -> DataCut:
        data_cut = None

        # use existing datacut
        if fxpair_id:
            try:
                data_cut = DataCut.objects.get(cut_time=date)
            except Exception as e:
                data_cut = None
 
        # create data cut
        if not fxpair_id or not data_cut:
            _, data_cut = DataCutService.create_cut(date=date, cut_type=self.data_cut_type)

        return data_cut

    def skip_import(self, date_time: datetime) -> bool:
        return (date_time.hour == self.eod_utc_hour or date_time.hour == self.benchmark_utc_hour)\
            and date_time.minute == 0
