import logging

from django.core.management.base import BaseCommand
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.core.utils.slack import decorator_to_post_exception_message_on_slack
from main.apps.hedge.services.eod_and_intra import EodAndIntraService

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to end_eod_flow_for_company."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    @decorator_to_post_exception_message_on_slack()
    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            time = Date.now()
            logging.info(f"End eod flow for company (ID={company_id}) at time {time}.")

            eod_service = EodAndIntraService(ref_date=time)
            eod_service.end_eod_flow_for_company(time=time, company=company_id)

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
