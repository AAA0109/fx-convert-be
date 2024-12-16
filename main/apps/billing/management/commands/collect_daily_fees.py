import logging

from django.core.management import BaseCommand, CommandParser

from main.apps.billing.services.daily_fee import DailyFeeService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Django command to collect daily fees"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--company_id", type=int, default=None,
                            help="Optional: Company ID")

    def handle(self, *args, **options):
        try:
            daily_fee_collector = DailyFeeService(options['company_id'])
            daily_fee_collector.execute()
            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
