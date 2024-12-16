import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandParser

from main.apps.core.utils.timer import timer
from main.apps.dataprovider.services.importer.provider_handler.ibkr.api.fx_spot_intra import \
    IbkrFxSpotIntraIBKRApiHandler
from main.apps.marketdata.models import DataCut
from datetime import datetime
import pytz

class Command(BaseCommand):
    help = 'Prefill fx spot intra ibkr historical data'
 
    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--years_to_fetch', type=float,
                            default=10, help='Years to fetch historical data. Default is 10 years')
        parser.add_argument('--reference_time', type=str,
                            default=None, help='Time will be converted to UTC timezone e.g. "2023-09-29 12:34:56" ')

    @timer(logging)
    def handle(self, *args, **options):
        try:
            years_to_fetch: float = options['years_to_fetch']
            reference_time: str = options['reference_time']

            logging.info(
                f"Prefilling fx spot intra ibkr historical data for "
                f"years_to_fetch={years_to_fetch}, reference_time={reference_time}")

            ibkr_fx_spot_intra_handler = IbkrFxSpotIntraIBKRApiHandler(
                data_cut_type=DataCut.CutType.INTRA,
                model=ContentType.objects.get(app_label="marketdata", model="fxspotintraibkr").model_class(),
            )
            if reference_time:
                utc_datetime = pytz.utc.localize(datetime.strptime(reference_time, '%Y-%m-%d %H:%M:%S'))
                ibkr_fx_spot_intra_handler.reference_time = utc_datetime
            ibkr_fx_spot_intra_handler.look_back_days = int(years_to_fetch * 365)
            ibkr_fx_spot_intra_handler.execute()
            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
