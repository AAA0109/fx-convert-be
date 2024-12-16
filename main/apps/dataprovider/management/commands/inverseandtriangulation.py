import logging

from django.core.management.base import BaseCommand, CommandParser

from main.apps.core.utils.timer import timer
from main.apps.dataprovider.services.backfiller.inverse_triangulator import InverseAndTriangulatorService


class Command(BaseCommand):
    help = 'Inverse and triangulates market data.'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--profile_id')
        parser.add_argument('--home_currency', type=str, default="USD",
                            help='The base or primary currency against which other currency rates are compared. '
                                 'Defaults to "USD".')
 
    @timer(logging)
    def handle(self, *args, **options):
        try:
            profile_id: int = options['profile_id']
            home_currency: str = options['home_currency']

            inverse_triangulation_service = InverseAndTriangulatorService(profile_id=profile_id, home_currency=home_currency)
            inverse_triangulation_service.execute()
            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)


class Command(BaseCommand):
    help = 'Inverse and triangulates market data.'

    def add_arguments(self, parser: CommandParser):
        parser.add_argument('--profile_id')
        parser.add_argument('--home_currency', type=str, default="USD",
                            help='The base or primary currency against which other currency rates are compared. '
                                 'Defaults to "USD".')

    @timer(logging)
    def handle(self, *args, **options):
        try:
            profile_id: int = options['profile_id']
            home_currency: str = options['home_currency']

            inverse_triangulation_service = InverseAndTriangulatorService(profile_id=profile_id, home_currency=home_currency)
            inverse_triangulation_service.execute()
            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
