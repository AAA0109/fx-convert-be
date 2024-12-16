import os
import re
import csv
import logging
from datetime import datetime
import pandas as pd
from typing import Dict, List, Iterable, Optional
from pytz import timezone

from django.db.models.fields.files import FieldFile
from django.core.files.storage import default_storage
import importlib

import main.apps.dataprovider as app
from main.apps.dataprovider.models.dataprovider import DataProvider
from main.apps.dataprovider.models.source import Source
from main.apps.dataprovider.models.profile import Profile
from main.apps.dataprovider.models.mapping import Mapping
from main.apps.dataprovider.models.value import Value
from main.apps.dataprovider.models.file import File
from main.apps.dataprovider.services.importer.provider_handler.corpay.xlsx.currency_capability import \
    CorPayCurrencyCapabilityHandler
from main.apps.dataprovider.services.importer.provider_handler.corpay.fx_forward import CorPayFxForwardHandler
from main.apps.dataprovider.services.importer.provider_handler.corpay.fx_spot import CorPayFxSpotHandler
from main.apps.dataprovider.services.importer.provider_handler.corpay.xlsx.currency_delivery_time import CurrencyDeliveryTimeHandler
from main.apps.dataprovider.services.importer.provider_handler.fincal.csv.tradingcalendar import TradingCalendarHandler
from main.apps.dataprovider.services.importer.provider_handler.fincal.csv.tradingholiday import TradingHolidaysHandler
from main.apps.dataprovider.services.importer.provider_handler.fincal.csv.tradingholidaycode import TradingHolidaysCodeHandler
from main.apps.dataprovider.services.importer.provider_handler.fincal.csv.tradingholidayinfo import TradingHolidaysInfoHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.model.fxspot_index import \
    IceAssetIndexFromFxSpotModelHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.future_contract import \
    IbkrFutureContarctApiHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.future_contract_intra import \
    IbkrFutureContractIntraApiHandler

from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.fx_spot_intra import \
    IbkrFxSpotIntraIBKRApiHandler

from main.apps.marketdata.models.marketdata import DataCut
from main.apps.core.utils.date import reformat_reuter_date, convert2datetime

from main.apps.dataprovider.services.importer.provider_handler.reuters.fx_spot import ReutersFxSpotHandler
from main.apps.dataprovider.services.importer.provider_handler.reuters.fx_spot_range import ReutersFxSpotRangeHandler
from main.apps.dataprovider.services.importer.provider_handler.reuters.option_strategy import ReutersOptionHandler
from main.apps.dataprovider.services.importer.provider_handler.reuters.option_strategy import \
    ReutersOptionStrategyHandler
from main.apps.dataprovider.services.importer.provider_handler.reuters.fx_forward import ReutersFxForwardHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.fx_spot import IceFxSpotHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.fx_spot_range import IceFxSpotRangeHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.fx_forward import IceFxForwardHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.option_strategy import IceOptionStrategyHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.option import IceOptionHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.ir_ois_rate import IceIrOisRateHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.ir_discount import IceIrDiscountHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.cm_spot import IceCmSpotHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.cm_instrument import IceCmInstrumentHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.cm_instrument_data import IceCmInstrumentDataHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.iborrate import IceIBORRateHandler
from main.apps.dataprovider.services.importer.provider_handler.ice.ir_govbond import IceGovBondHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.fx_spot import IbkrFxSpotApiHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.fx_spot_range import IbkrFxSpotRangeApiHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.trading_calendar import \
    IbkrTradingCalendarHandler

from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.currency_margin import \
    IbkrCurrencyMarginHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.benchmark_rate import IbkrBenchmarkRateHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.interest_rate import IbkrInterestRateHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.html.fxspot_margin import IbkrFxSpotMarginHandler
from main.apps.dataprovider.services.importer.provider_handler.country.country_iso_code import CountryISOHandler
from main.apps.dataprovider.services.importer.provider_handler.country.country_currency_mapping import \
    CountryMappingHandler
from main.apps.dataprovider.services.importer.provider_handler.spi.social_progress_index import \
    SocialProgressIndexHandler
from main.apps.dataprovider.services.importer.provider_handler.ndl.sge import SGEHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.csv.future_contract import \
    IbkrFutureContractHandler
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.future_calender import \
    IbkrFutureCalendarHandler


class DataImporter(object):
    """
    Service class used for importing market data from CSV to DB
    """
    APP_PATH = os.path.dirname(app.__file__)
    STORAGE_PATH = APP_PATH + '/storage'
    CSV_PATH = STORAGE_PATH + '/csv'
    profile_id: int = None
    options: dict = {}

    def __init__(self, profile_id: int, options: Optional[dict] = {}):
        self.profile_id = profile_id
        self.options = options

    def execute(self):
        """ Main method to run the data import """
        self._process_data_providers()

    # ==================
    # Private
    # ==================

    def _get_raw_data(self):
        return

    def _synchronize_data(self, data):
        return

    def _sanatize_data(self, data):
        return

    def _process_data_providers(self):
        self._process_model()
        self._process_csv()
        self._process_api()
        self._process_html()
        self._process_txt()
        self._process_json()
        self._process_json_file()
        self._process_xlsx()

    def _process_html(self):
        query_set = Profile.objects.filter(
            file_format=Profile.FileFormat.HTML,
            enabled=True,
            source__enabled=True,
            source__data_provider__enabled=True,
            target__isnull=False
        )
        if self.profile_id is not None:
            query_set = query_set.filter(id=self.profile_id)
        for profile in query_set:
            logging.info(f"Starting import for profile: {profile.id}")
            source = profile.source
            data_provider = source.data_provider
            target = profile.target
            if data_provider.provider_handler == DataProvider.ProviderHandlers.IBKR:
                if source.data_type == Source.DataType.IBKR_WEB:
                    if target.model == 'currencymargin':
                        ibkr_currency_margin_handler = IbkrCurrencyMarginHandler(data_cut_type=profile.data_cut_type,
                                                                                 url=profile.url,
                                                                                 model=target.model_class(),
                                                                                 broker=profile.source.data_provider.broker)
                        ibkr_currency_margin_handler.execute()
                    if target.model == 'benchmarkrate':
                        ibkr_benchmark_rate_handler = IbkrBenchmarkRateHandler(data_cut_type=profile.data_cut_type,
                                                                               url=profile.url,
                                                                               model=target.model_class(),
                                                                               broker=profile.source.data_provider.broker)
                        ibkr_benchmark_rate_handler.execute()
                    if target.model == 'interestrate':
                        ibkr_interest_rate_handler = IbkrInterestRateHandler(data_cut_type=profile.data_cut_type,
                                                                             url=profile.url,
                                                                             model=target.model_class(),
                                                                             broker=profile.source.data_provider.broker)
                        ibkr_interest_rate_handler.execute()
                    if target.model == 'fxspotmargin':
                        ibkr_fx_spot_margin_handler = IbkrFxSpotMarginHandler(data_cut_type=profile.data_cut_type,
                                                                              url=profile.url,
                                                                              model=target.model_class(),
                                                                              broker=profile.source.data_provider.broker)
                        ibkr_fx_spot_margin_handler.execute()
                    if target.model in ['futurecontractintra']:
                        ibkr_future_contract_handler = IbkrFutureContractIntraApiHandler(
                            data_cut_type=profile.data_cut_type,
                            model=target.model_class())
                        ibkr_future_contract_handler.execute()

    def _process_api(self):
        query_set = Profile.objects.filter(
            file_format=Profile.FileFormat.API,
            enabled=True,
            source__enabled=True,
            source__data_provider__enabled=True,
            target__isnull=False
        )
        if self.profile_id is not None:
            query_set = query_set.filter(id=self.profile_id)
        for profile in query_set:
            logging.info(f"Starting import for profile: {profile.id}")
            source = profile.source
            data_provider = source.data_provider
            target = profile.target
            if data_provider.provider_handler == DataProvider.ProviderHandlers.IBKR:
                if source.data_type == Source.DataType.IBKR_TWS:
                    if target.model in ['fxspotrange', 'fxspotrangeintra']:
                        ibkr_fx_spot_range_handler = IbkrFxSpotRangeApiHandler(data_cut_type=profile.data_cut_type,
                                                                               model=target.model_class())
                        ibkr_fx_spot_range_handler.execute()
                    if target.model in ['fxspot', 'fxspotintra']:
                        ibkr_fx_spot_handler = IbkrFxSpotApiHandler(data_cut_type=profile.data_cut_type,
                                                                    model=target.model_class())
                        ibkr_fx_spot_handler.execute()
                    if target.model == 'tradingcalendar':
                        ibkr_trading_calendar_handler = IbkrTradingCalendarHandler(data_cut_type=profile.data_cut_type,
                                                                                   model=target.model_class())
                        ibkr_trading_calendar_handler.execute()
                    if target.model == 'futurecontract':
                        ibkr_future_contract_handler = IbkrFutureContarctApiHandler(
                            data_cut_type=profile.data_cut_type, model=target.model_class())
                        ibkr_future_contract_handler.execute()
                    if target.model in ['futureliquidhours', 'futuretradinghours']:
                        ibkr_future_calender_handler = IbkrFutureCalendarHandler(data_cut_type=profile.data_cut_type,
                                                                                 model=target.model_class())
                        ibkr_future_calender_handler.execute()
                    if target.model == 'fxspotintraibkr':
                        ibkr_fx_spot_intra_handler = IbkrFxSpotIntraIBKRApiHandler(
                            data_cut_type=profile.data_cut_type,
                            model=target.model_class())
                        ibkr_fx_spot_intra_handler.execute()
            if data_provider.provider_handler == DataProvider.ProviderHandlers.CORPAY:
                if source.data_type == Source.DataType.CORPAY_API:
                    if target.model in ['corpayfxforward']:
                        corpay_fx_forward_handler = CorPayFxForwardHandler(data_cut_type=profile.data_cut_type,
                                                                           model=target.model_class(),
                                                                            options=self.options)
                        corpay_fx_forward_handler.execute()
                    if target.model in ['corpayfxspot']:
                        corpay_fx_spot_handler = CorPayFxSpotHandler(data_cut_type=profile.data_cut_type,
                                                                     model=target.model_class(), options=self.options)
                        corpay_fx_spot_handler.execute()

    def _process_csv(self):
        query_set = File.objects.filter(
            status__in=[File.FileStatus.DOWNLOADED, File.FileStatus.ERROR],
            profile__enabled=True,
            source__enabled=True,
            data_provider__enabled=True,
            profile__file_format=Profile.FileFormat.CSV,
            profile__target__isnull=False
        )
        if self.profile_id is not None:
            query_set = query_set.filter(profile_id=self.profile_id)
        for downloaded_file in query_set:
            profile = downloaded_file.profile
            logging.info(f"Starting import for profile: {profile.id}")
            try:
                downloaded_file.status = File.FileStatus.PREPROCESSING
                downloaded_file.save()
                fpath = self._get_filepath(downloaded_file, 'csv')
                self._import_csv(fpath=fpath, profile=profile)
                downloaded_file.status = File.FileStatus.PREPROCESSED
                downloaded_file.save()
            except Exception as e:
                downloaded_file.status = File.FileStatus.ERROR
                downloaded_file.save()
                logging.error(e)
                raise e

    def _import_csv(self, fpath: str, profile: Profile):
        chunksize = 10000
        source = profile.source
        data_provider = source.data_provider
        handler = data_provider.provider_handler
        target = profile.target
        data_provider_mappings = self._get_data_provider_mappings(data_provider)
        profile_mappings = self._get_profile_mappings(profile)
        logging.info(f"importing csv: {fpath}")
        if handler == data_provider.ProviderHandlers.REUTERS:
            if target.model in ['fxspot', 'fxspoteod']:
                with pd.read_csv(fpath, chunksize=chunksize) as reader:
                    for df in reader:
                        df['date'] = df['Date'].apply(reformat_reuter_date, tz='US/Eastern')
                        reuters_fx_spot_handler = ReutersFxSpotHandler(
                            df=df,
                            data_provider_mappings=data_provider_mappings,
                            profile_mappings=profile_mappings,
                            data_cut_type=profile.data_cut_type,
                            model=target.model_class()
                        )
                        reuters_fx_spot_handler.execute()

            if target.model in ['fxspotrange', 'fxspotrangeeod']:
                with pd.read_csv(fpath, chunksize=chunksize) as reader:
                    for df in reader:
                        df['date'] = df['Date'].apply(reformat_reuter_date, tz='US/Eastern')
                        reuters_fx_spot_range_handler = ReutersFxSpotRangeHandler(
                            df=df,
                            data_provider_mappings=data_provider_mappings,
                            profile_mappings=profile_mappings,
                            data_cut_type=profile.data_cut_type,
                            model=target.model_class()
                        )
                        reuters_fx_spot_range_handler.execute()

            if target.model == 'option':
                with pd.read_csv(fpath, chunksize=chunksize) as reader:
                    for df in reader:
                        df['date'] = df['Trade Date'].apply(convert2datetime, args=('17:00:00',)).apply(
                            lambda x: x.tz_localize('US/Eastern'))
                        reuters_option_handler = ReutersOptionHandler(
                            df=df,
                            data_provider_mappings=data_provider_mappings,
                            profile_mappings=profile_mappings,
                            data_cut_type=profile.data_cut_type,
                            model=target.model_class()
                        )
                        reuters_option_handler.execute()

            if target.model == 'optionstrategy':
                with pd.read_csv(fpath, chunksize=chunksize) as reader:
                    for df in reader:
                        df['date'] = df['Trade Date'].apply(convert2datetime, args=('17:00:00',)).apply(
                            lambda x: x.tz_localize('US/Eastern'))
                        reuters_option_strategy_handler = ReutersOptionStrategyHandler(
                            df=df,
                            data_provider_mappings=data_provider_mappings,
                            profile_mappings=profile_mappings,
                            data_cut_type=profile.data_cut_type,
                            model=target.model_class()
                        )
                        reuters_option_strategy_handler.execute()

            if target.model == 'fxforward':
                with pd.read_csv(fpath, chunksize=chunksize) as reader:
                    for df in reader:
                        df['date'] = df['Trade Date'].apply(convert2datetime, args=('17:00:00',)).apply(
                            lambda x: x.tz_localize('US/Eastern'))
                        reuters_fx_forward_handler = ReutersFxForwardHandler(
                            df=df,
                            data_provider_mappings=data_provider_mappings,
                            profile_mappings=profile_mappings,
                            data_cut_type=profile.data_cut_type,
                            model=target.model_class()
                        )
                        reuters_fx_forward_handler.execute()

        if handler == data_provider.ProviderHandlers.ICE:
            timestamp, skiprows = self._get_csv_timestamp(fpath)
            df = pd.read_csv(fpath, skiprows=skiprows)
            df['date'] = timestamp

            if target.model in ['fxspot', 'fxspoteod', 'fxspotbenchmark']:
                ice_fx_spot_handler = IceFxSpotHandler(
                    df=df,
                    data_provider_mappings=data_provider_mappings,
                    profile_mappings=profile_mappings,
                    data_cut_type=profile.data_cut_type,
                    model=target.model_class()
                )
                ice_fx_spot_handler.execute()
            if target.model in ['fxspotrange', 'fxspotrangeeod']:
                ice_fx_spot_range_handler = IceFxSpotRangeHandler(
                    df=df,
                    data_provider_mappings=data_provider_mappings,
                    profile_mappings=profile_mappings,
                    data_cut_type=profile.data_cut_type,
                    model=target.model_class()
                )
                ice_fx_spot_range_handler.execute()
            if target.model == 'fxforward':
                filter = df['SDKey'].str.contains('FX_TERMSTRUCTURECALCULATED')
                df_trim = df.loc[filter]
                if len(df_trim) > 0:
                    ice_fx_forward_handler = IceFxForwardHandler(
                        df=df_trim,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=profile.data_cut_type,
                        model=target.model_class()
                    )
                    ice_fx_forward_handler.execute()
            if target.model == 'fxoptionstrategy':
                filter = df['SDKey'].str.contains('FX_TERMSTRUCTURECALCULATED')
                df_trim = df.loc[filter]
                if len(df_trim) > 0:
                    ice_option_strategy_handler = IceOptionStrategyHandler(
                        df=df_trim,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=profile.data_cut_type,
                        model=target.model_class()
                    )
                    ice_option_strategy_handler.execute()
            if target.model == 'fxoption':
                filter = df['SDKey'].str.contains('FX_VOLATILITYSURFACE')
                df_trim = df.loc[filter]
                if len(df_trim) > 0:
                    ice_option_handler = IceOptionHandler(
                        df=df_trim,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=profile.data_cut_type,
                        model=target.model_class()
                    )
                    ice_option_handler.execute()
            if target.model == 'oisrate':
                ice_ois_rate_handler = IceIrOisRateHandler(
                    df=df,
                    data_provider_mappings=data_provider_mappings,
                    profile_mappings=profile_mappings,
                    data_cut_type=profile.data_cut_type,
                    model=target.model_class()
                )
                ice_ois_rate_handler.execute()
            if target.model == 'irdiscount':
                ice_ir_discount_handler = IceIrDiscountHandler(
                    df=df,
                    data_provider_mappings=data_provider_mappings,
                    profile_mappings=profile_mappings,
                    data_cut_type=profile.data_cut_type,
                    model=target.model_class()
                )
                ice_ir_discount_handler.execute()
            if target.model == 'cmspot':
                filter = df['SDKey'].str.contains('(FX_SPT_XAUUSD|FX_SPT_XAGUSD)', regex=True)
                df_trim = df.loc[filter]
                if len(df_trim) > 0:
                    ice_cm_spot_handler = IceCmSpotHandler(
                        df=df_trim,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=profile.data_cut_type,
                        model=target.model_class()
                    )
                    ice_cm_spot_handler.execute()
            if target.model == 'cminstrument':
                filter = df['SDKey'].str.contains('CM_FUTALL_.*', regex=True)
                df_trim = df.loc[filter]
                if len(df_trim) > 0:
                    ice_cm_instrument_handler = IceCmInstrumentHandler(
                        df=df_trim,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=profile.data_cut_type,
                        model=target.model_class()
                    )
                    ice_cm_instrument_handler.execute()
            if target.model == 'cminstrumentdata':
                filter = df['SDKey'].str.contains('CM_FUTALL_.*', regex=True)
                df_trim = df.loc[filter]
                if len(df_trim) > 0:
                    ice_cm_instrument_data_handler = IceCmInstrumentDataHandler(
                        df=df_trim,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=profile.data_cut_type,
                        model=target.model_class()
                    )
                    ice_cm_instrument_data_handler.execute()

            if target.model == 'iborrate':
                filter = df['SDKey'].str.contains('IR_YC_.*', regex=True)
                df_trim = df.loc[filter]
                if len(df_trim) > 0:
                    ice_iborrate_data_handler = IceIBORRateHandler(
                        df=df_trim,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=DataCut.CutType.EOD,
                        model=target.model_class()
                    )
                    ice_iborrate_data_handler.execute()

            if target.model == 'govbond':
                ice_govbond_data_handler = IceGovBondHandler(
                    df=df,
                    data_provider_mappings=data_provider_mappings,
                    profile_mappings=profile_mappings,
                    data_cut_type=DataCut.CutType.EOD,
                    model=target.model_class()
                )
                ice_govbond_data_handler.execute()

        if handler == data_provider.ProviderHandlers.CORPAY:
            df = pd.read_csv(fpath)

            if profile.file_format == Profile.FileFormat.CSV:
                if target.model in ['fxforwardcosts']:
                    corpay_fx_forward_costs_handler = CorPayFxForwardCostHandler(
                        df=df,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=DataCut.CutType.EOD,
                        model=target.model_class()
                    )
                    corpay_fx_forward_costs_handler.execute()

        if handler == data_provider.ProviderHandlers.IBKR:
            df = pd.read_csv(fpath)

            if profile.file_format == Profile.FileFormat.CSV:
                if target.model in ['futurecontract']:
                    ibkr_csv_contract_handler = IbkrFutureContractHandler(
                        df=df,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=DataCut.CutType.EOD,
                        model=target.model_class()
                    )
                    ibkr_csv_contract_handler.execute()

        if handler == data_provider.ProviderHandlers.FIN_CAL:
            if target.model == 'tradingholidayscodefincal':
                df = pd.read_csv(fpath)
                fincal_tradingholidaycode_handler = TradingHolidaysCodeHandler(
                        df=df,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=DataCut.CutType.EOD,
                        model=target.model_class()
                    )
                fincal_tradingholidaycode_handler.execute()
            elif target.model == 'tradingholidaysinfofincal':
                df = pd.read_csv(fpath)
                fincal_tradingholidayinfo_handler = TradingHolidaysInfoHandler(
                        df=df,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=DataCut.CutType.EOD,
                        model=target.model_class()
                    )
                fincal_tradingholidayinfo_handler.execute()
            elif target.model == 'tradingholidaysfincal':
                df = pd.read_csv(fpath)
                fincal_tradingholiday_handler = TradingHolidaysHandler(
                        df=df,
                        data_provider_mappings=data_provider_mappings,
                        profile_mappings=profile_mappings,
                        data_cut_type=DataCut.CutType.EOD,
                        model=target.model_class()
                    )
                fincal_tradingholiday_handler.execute()
            elif target.model == 'tradingcalendarfincal':
                with pd.read_csv(fpath, chunksize=chunksize) as reader:
                    for df in reader:
                        fincal_tradingcalender_handler = TradingCalendarHandler(
                                df=df,
                                data_provider_mappings=data_provider_mappings,
                                profile_mappings=profile_mappings,
                                data_cut_type=DataCut.CutType.EOD,
                                model=target.model_class()
                            )
                        fincal_tradingcalender_handler.execute()


    def _get_profile_mappings(self, profile: Profile) -> Dict[str, List[dict]]:
        mappings = profile.mapping_set.all()
        return self._get_mappings(mappings)

    def _get_data_provider_mappings(self, data_provider: DataProvider):
        mappings = data_provider.mapping_set.all()
        return self._get_mappings(mappings)

    def _get_mappings(self, mappings: Iterable[Mapping]) -> Dict[str, List[dict]]:
        output = {}
        for mapping in mappings:
            column_name = mapping.column_name
            values = mapping.value_set.all()
            value_map = {}
            if values:
                for value in values:
                    if value in value_map:
                        continue
                    if value.mapping_type == Value.MappingType.FX_PAIR:
                        value_map[value.from_value] = value.to_fxpair_id
                    elif value.mapping_type == Value.MappingType.CURRENCY:
                        value_map[value.from_value] = value.to_currency_id
                    elif value.mapping_type == Value.MappingType.IR_CURVE:
                        value_map[value.from_value] = value.to_ircurve_id
                    elif value.mapping_type == Value.MappingType.STRING:
                        value_map[value.from_value] = value.to_value
                if column_name in output:
                    output[column_name].append(value_map)
                else:
                    output[column_name] = [value_map]
        return output

    def _get_csv_timestamp(self, fpath):
        with open(fpath, 'r') as csv_file:
            csv_reader = csv.reader(csv_file)
            i = 0
            for line in csv_reader:
                if i == 0:
                    date_match = re.search(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})", line[0])
                if i == 1:
                    time_match = re.search(r"[CcUuTt]{3}=(?P<hour>\d{2})(?P<minute>\d{2})(?P<timezone>.*)", line[0])
                    break
                i += 1
        skiprows = bool(date_match) + bool(time_match)

        # extract time from path
        head_tail = os.path.split(fpath)
        if date_match is None:
            date_match = re.search(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})", head_tail[1])
        if time_match is None:
            time_match = re.search(r"(?P<hour>\d{2})(?P<minute>\d{2})_(?P<timezone>\w{2})", head_tail[1])

        if time_match is not None:
            tz = self._get_timezone(time_match)
            timestamp = datetime(
                int(date_match.group('year')),
                int(date_match.group('month')),
                int(date_match.group('day')),
                int(time_match.group('hour')),
                int(time_match.group('minute')),
                0
            )
            timestamp = tz.localize(timestamp)
            return timestamp, skiprows
        elif date_match is not None:
            # todo: make sure utc and ny time
            tz = timezone('UTC')
            timestamp = datetime(
                int(date_match.group('year')),
                int(date_match.group('month')),
                int(date_match.group('day')),
                0,
                0,
                0
            )
            timestamp = tz.localize(timestamp)
            return timestamp, skiprows
        else:
            raise RuntimeError("date and timezone are not detected")

    @staticmethod
    def _get_timezone(time_match):
        if time_match.group('timezone') == 'NY':
            tz = timezone('US/Eastern')
        else:
            tz = timezone('UTC')
        return tz

    def _get_filepath(self, downloaded_file: FieldFile, file_type: str):
        if default_storage.__class__.__name__ == 'GoogleCloudStorage':
            tmp_fpath = f"/tmp/tmp.{file_type}"
            downloaded_file.file.open()
            results = downloaded_file.file.read()
            with open(tmp_fpath, 'wb') as f:
                f.write(results)
            return tmp_fpath
        return downloaded_file.file.path

    def _process_json(self):
        query_set = Profile.objects.filter(
            file_format=Profile.FileFormat.JSON,
            enabled=True,
            source__enabled=True,
            source__data_provider__enabled=True,
            target__isnull=False
        )

        if self.profile_id is not None:
            query_set = query_set.filter(id=self.profile_id)

        for profile in query_set:
            logging.info(f"Starting import for profile: {profile.id} profile name: {profile.name}")
            source = profile.source
            data_provider = source.data_provider
            target = profile.target
            if data_provider.provider_handler == DataProvider.ProviderHandlers.NDL:
                if source.data_type == Source.DataType.REST_API:
                    if target.model == 'sge':
                        country_iso_handler = SGEHandler(data_cut_type=profile.data_cut_type, url=profile.url,
                                                         model=target.model_class())
                        country_iso_handler.execute()

    def _process_json_file(self):
        query_set = File.objects.filter(
            status__in=[File.FileStatus.DOWNLOADED, File.FileStatus.ERROR],
            profile__enabled=True,
            source__enabled=True,
            data_provider__enabled=True,
            profile__file_format=Profile.FileFormat.JSON,
            profile__target__isnull=False
        )
        if self.profile_id is not None:
            query_set = query_set.filter(profile_id=self.profile_id)
        for downloaded_file in query_set:
            profile = downloaded_file.profile
            logging.info(f"Starting import for profile: {profile.id}")
            try:
                downloaded_file.status = File.FileStatus.PREPROCESSING
                downloaded_file.save()
                fpath = self._get_filepath(downloaded_file, "json")
                self._import_json(fpath=fpath, profile=profile)
                downloaded_file.status = File.FileStatus.PREPROCESSED
                downloaded_file.save()
            except Exception as e:
                downloaded_file.status = File.FileStatus.ERROR
                downloaded_file.save()
                logging.error(e)
                raise e

    def _import_json(self, fpath: str, profile: Profile):
        source = profile.source
        data_provider = source.data_provider
        handler = data_provider.provider_handler
        target = profile.target
        logging.info(f"importing json: {fpath}")
        if handler == data_provider.ProviderHandlers.COUNTRY:
            if target.model == 'country':
                country_iso_handler = CountryMappingHandler(data_cut_type=profile.data_cut_type, url=profile.url,
                                                            model=target.model_class(), file_path=fpath)
                country_iso_handler.execute()

    def _process_txt(self):
        query_set = Profile.objects.filter(
            file_format=Profile.FileFormat.TXT,
            enabled=True,
            source__enabled=True,
            source__data_provider__enabled=True,
            target__isnull=False
        )
        if self.profile_id is not None:
            query_set = query_set.filter(id=self.profile_id)
        for profile in query_set:
            logging.info(f"Starting import for profile: {profile.id}")
            source = profile.source
            data_provider = source.data_provider
            target = profile.target
            if data_provider.provider_handler == DataProvider.ProviderHandlers.COUNTRY:
                if source.data_type == Source.DataType.REST_API:
                    if target.model == 'country':
                        country_iso_handler = CountryISOHandler(data_cut_type=profile.data_cut_type, url=profile.url,
                                                                model=target.model_class())
                        country_iso_handler.execute()

    def _process_xlsx(self):
        query_set = File.objects.filter(
            status__in=[File.FileStatus.DOWNLOADED, File.FileStatus.ERROR],
            profile__enabled=True,
            source__enabled=True,
            data_provider__enabled=True,
            profile__file_format=Profile.FileFormat.XLSX,
            profile__target__isnull=False
        )
        if self.profile_id is not None:
            query_set = query_set.filter(profile_id=self.profile_id)
        for downloaded_file in query_set:
            profile = downloaded_file.profile
            logging.info(f"Starting import for profile: {profile.id}")
            try:
                downloaded_file.status = File.FileStatus.PREPROCESSING
                downloaded_file.save()
                fpath = self._get_filepath(downloaded_file, 'xlsx')
                self._import_xlsx(fpath=fpath, profile=profile)
                downloaded_file.status = File.FileStatus.PREPROCESSED
                downloaded_file.save()
            except Exception as e:
                downloaded_file.status = File.FileStatus.ERROR
                downloaded_file.save()
                logging.error(e)
                raise e

    def _import_xlsx(self, fpath: str, profile: Profile):
        source = profile.source
        data_provider = source.data_provider
        handler = data_provider.provider_handler
        target = profile.target
        logging.info(f"importing xlsx: {fpath}")
        if handler == DataProvider.ProviderHandlers.SPI:
            if target.model == 'stabilityindex':
                df = pd.read_excel(fpath, skiprows=[0], usecols='A:CC', sheet_name="2011-2022 SPI data")
                spi_handler = SocialProgressIndexHandler(
                    df=df,
                    fpath=fpath,
                    data_cut_type=profile.data_cut_type,
                    model=target.model_class()
                )
                spi_handler.execute()
        if handler == DataProvider.ProviderHandlers.CORPAY:
            if target.model == 'currencydefinition':
                df = pd.read_excel(fpath, usecols='A:I', sheet_name="Corpay Product Availability")
                currency_capability_handler = CorPayCurrencyCapabilityHandler(
                    df=df,
                    fpath=fpath,
                    data_cut_type=profile.data_cut_type,
                    model=target.model_class()
                )
                currency_capability_handler.execute()
            if target.model == 'deliverytime':
                df = pd.read_excel(fpath, usecols='A:F', sheet_name="Payment Timeframes")
                currency_deliverytime_handler = CurrencyDeliveryTimeHandler(
                    df=df,
                    fpath=fpath,
                    data_cut_type=profile.data_cut_type,
                    model=target.model_class()
                )
                currency_deliverytime_handler.execute()

    def _process_model(self):
        query_set = Profile.objects.filter(
            file_format=Profile.FileFormat.MODEL,
            enabled=True,
            source__enabled=True,
            source__data_provider__enabled=True,
            target__isnull=False
        )
        if self.profile_id is not None:
            query_set = query_set.filter(id=self.profile_id)
        for profile in query_set:
            logging.info(f"Starting import for profile: {profile.id}")
            source = profile.source
            data_provider = source.data_provider
            target = profile.target
            if data_provider.provider_handler == DataProvider.ProviderHandlers.ICE:
                if source.data_type == Source.DataType.MODEL:
                    if target.model in ['index']:
                        dxy_fxspot_handler_handler = IceAssetIndexFromFxSpotModelHandler(
                            data_cut_type=profile.data_cut_type, model=target.model_class())
                        dxy_fxspot_handler_handler.execute()

    def get_option(self, key: str) -> str:
        return self.options.get(key)

    def set_option(self, key: str, value: str) -> None:
        self.options[key] = value

    def set_options(self, options: dict) -> None:
        self.options = options
