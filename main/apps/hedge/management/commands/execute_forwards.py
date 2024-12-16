import logging

from django.core.management.base import BaseCommand

from main.apps.account.models import Company
from main.apps.core.utils.slack import decorator_to_post_exception_message_on_slack
from main.apps.corpay.services.corpay import CorPayExecutionServiceFactory
from main.apps.hedge.services.forward_execution import ForwardExecutionService

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to execute all pending forwards and close expired ones."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    @decorator_to_post_exception_message_on_slack()
    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            logging.info(f"Pending Forward Command flow for company (ID={company_id}).")

            factory = CorPayExecutionServiceFactory()
            execution_service = factory.for_company(company)
            ForwardExecutionService(execution_service).update_forwards(company)

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
