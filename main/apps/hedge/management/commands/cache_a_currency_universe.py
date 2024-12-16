import logging

from django.core.management.base import BaseCommand
from hdlib.DateTime.Date import Date

from main.apps.currency.models import Currency
from main.apps.hedge.services.hedger import caching_make_cntr_currency_universe

logger = logging.getLogger("root")


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--currency_id", type=int, help="Required: Currency ID")
        parser.add_argument("--ref_date", type=str, help="Ref Date", default=Date.today().date().__str__())


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to cache_a_currency_universe."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            currency_id = options["currency_id"]
            ref_date: Date = Date.from_str(options["ref_date"])

            logging.info(f"Running cache_a_currency_universe "
                         f"for currency (ID={currency_id}) "
                         f"and ref_date {ref_date}")

            domestic = Currency.objects.get(pk=currency_id)

            caching_make_cntr_currency_universe(domestic=domestic,
                                                ref_date=ref_date,
                                                bypass_errors=True)

            logging.info(f"Finished cache_a_currency_universe "
                         f"for currency (ID={currency_id}) "
                         f"and ref_date {ref_date}")

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
