import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandParser

from main.apps.dataprovider.services.importer.provider_handler.ice.model.fxspot_index import IceAssetIndexFromFxSpotModelHandler
from main.apps.marketdata.models import DataCut
from datetime import datetime
import pytz


class Command(BaseCommand):
    help = 'Calculate index value for fx spot historical data'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--years_to_fetch', type=float,
                            default=10, help='Years to fetch historical data. Default is 10 years')
        parser.add_argument('--reference_date', type=str,
                            default=None, help='Date will be converted to UTC timezone e.g. "2023-09-29" ')

    def handle(self, *args, **options):
        try:
            years_to_fetch: float = options['years_to_fetch']
            reference_date: str = options['reference_date']

            logging.info(
                f"Calculate index value for fx spot historical data for "
                f"years_to_fetch={years_to_fetch}, reference_date={reference_date}")

            ice_index_fx_spot_handler = IceAssetIndexFromFxSpotModelHandler(
                data_cut_type=DataCut.CutType.EOD,
                model=ContentType.objects.get(
                    app_label="marketdata", model="index").model_class(),
            )
            if reference_date:
                utc_datetime = pytz.utc.localize(
                    datetime.strptime(reference_date, '%Y-%m-%d'))
                ice_index_fx_spot_handler.history_date_start = utc_datetime
            ice_index_fx_spot_handler.history_back_days = int(
                years_to_fetch * 365)
            ice_index_fx_spot_handler.execute()
            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
