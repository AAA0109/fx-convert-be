import logging

from django.core.management.base import BaseCommand
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.core.utils.slack import decorator_to_post_exception_message_on_slack
from main.apps.corpay.services.corpay import (
    CorPayExecutionServiceFactory,
)
from main.apps.hedge.services.drawdown_forwards import DrowdownService

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to execute drow down all forwards that are expired."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    @decorator_to_post_exception_message_on_slack()
    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            logger.debug(f"Drow down forward command flow for company (ID={company_id}).")

            logger.debug(f"Get execution service for company (ID={company_id}).")
            factory = CorPayExecutionServiceFactory()
            logger.debug(f"Got execution service for company (ID={company_id}).")
            logger.debug(f"Get execution service for company (ID={company_id}).")
            execution_service = factory.for_company(company)
            logger.debug(f"Got execution service for company (ID={company_id}).")
            logger.debug(f"Start executing command for company (ID={company_id}).")
            DrowdownService(execution_service).draw_down(Date.today(), company)
            logger.debug(f"Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
