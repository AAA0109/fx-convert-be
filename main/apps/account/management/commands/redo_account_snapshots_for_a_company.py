import logging

from django.core.management.base import BaseCommand

from main.apps.account.models import Company
from main.apps.account.services.snapshot import AccountSnapshotsService

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    def add_default_arguments(self, parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to redo account snapshots for a company."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]

            logger.debug(f"Starting command to redo account snapshots for company={company_id}")

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            service = AccountSnapshotsService()
            service.redo_snapshots_for_company(company=company)

            logger.debug(f"Finished command to redo account snapshots for company={company_id}")
            logger.debug("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
