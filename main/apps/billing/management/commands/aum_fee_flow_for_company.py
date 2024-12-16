import logging

from django.core.management.base import BaseCommand

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company
from main.apps.billing.services.aum_fee import AumFeeUpdateService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to aum_fee_flow_for_company."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            time = Date.now()
            logging.info(f"AUM fee update flow for company (ID={company_id}) at time {time}.")

            fx_provider = FxSpotProvider()
            spot_cache = fx_provider.get_spot_cache(time=time)
            AumFeeUpdateService().run_eod(company=company, date=time, spot_fx_cache=spot_cache)

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
