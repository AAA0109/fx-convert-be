import logging

from django.core.management.base import BaseCommand, CommandParser

from main.apps.core.utils.timer import timer
from main.apps.dataprovider.services.backfiller.triangulation_handler.fxforward import \
    FxForwardTriangulationBackfiller
from main.apps.dataprovider.services.backfiller.triangulation_handler.fxspot import FxSpotTriangulationBackfiller


class Command(BaseCommand):
    help = 'Calculate triangulated data and backfill the data in the marketdata table.'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--triangulate_currency', type=str, help='Currency for triangulation (e.g., EUR, GBP).')
        parser.add_argument('--home_currency', type=str, default="USD", help='Home currency, default "USD".')
        parser.add_argument('--table', type=str, help='Marketdata Table that we want to backfill.')
        parser.add_argument('--start_date', type=str, default=None, help='Start date for data range (YYYY-MM-DD).')
        parser.add_argument('--end_date', type=str, default=None, help='End date for data range (YYYY-MM-DD).')

    @timer(logging)
    def handle(self, *args, **options):
        try:
            if options.get('table') == "fxspot":
                model_class = FxSpotTriangulationBackfiller
            elif options.get('table') == "fxforward":
                model_class = FxForwardTriangulationBackfiller
            else:
                raise Exception("Invalid table name")

            backfiller = model_class(
                triangulate_currency=options.get('triangulate_currency'),
                home_currency=options.get('home_currency'),
                start_date=options.get('start_date'),
                end_date=options.get('end_date')
            )
            backfiller.execute()

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
