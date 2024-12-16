import datetime as dt
import logging
import time

from django.core.management.base import BaseCommand
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company, Account
from main.apps.oems.services.order_service import OrderService

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to check if company orders are done."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)
        parser.add_argument("--retry_time", type=int, help="Retry time in seconds")
        parser.add_argument("--timeout", type=int, help="Timeout in minutes")

    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]
            retry_time = options["retry_time"] or 15
            timeout_in_minutes = options["timeout"] or 15

            timeout_delta = dt.timedelta(minutes=timeout_in_minutes)
            end_timestamp = Date.now().__add__(amount=timeout_delta).timestamp()

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            logging.info(f"Start checking if company ({company.name}) orders are done.")
            order_service = OrderService()
            if Account.has_live_accounts(company=company):
                while not order_service.are_company_orders_done(company=company):
                    if Date.now().timestamp() > end_timestamp:
                        raise Exception(f"Timeout for OMS to fill orders for {company.name}.")

                    logger.debug(
                        f"Waiting for OMS to fill orders for {company.name}. "
                        f"Waiting {retry_time} seconds...")
                    time.sleep(retry_time)
            logger.debug(f"Orders filled for {company.name}.")

            logging.info("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
