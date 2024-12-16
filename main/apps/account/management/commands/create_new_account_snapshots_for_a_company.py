import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.account.services.snapshot import AccountSnapshotsService

logger = logging.getLogger(__name__)


class TaskDefaultArgumentsMixin:

    @staticmethod
    def add_default_arguments(parser):
        parser.add_argument("--company_id", type=int, help="Required: Company ID")
        parser.add_argument("--start_date", type=str, help="Start date")
        parser.add_argument("--end_date", type=str, help="End date")
        parser.add_argument("--hour", type=int, help="Hour", default=13)
        parser.add_argument("--minute", type=int, help="Minute", default=0)


class Command(TaskDefaultArgumentsMixin, BaseCommand):
    help = "Django command to create new account snapshots for a company."

    def add_arguments(self, parser):
        self.add_default_arguments(parser)

    def handle(self, *args, **options):
        try:
            company_id = options["company_id"]
            str_start_date = options["start_date"]
            str_end_date = options["end_date"]
            hour = options["hour"]
            minute = options["minute"]

            try:
                assert company_id
                assert str_start_date
                assert str_end_date

                start_date = datetime.strptime(str_start_date, '%m-%d-%Y')
                end_date = datetime.strptime(str_end_date, '%m-%d-%Y')

                # Set the times, making sure the hours and minute are as chosen.
                hd_start_date = Date.create(
                    year=start_date.year,
                    month=start_date.month,
                    day=start_date.day,
                    hour=hour,
                    minute=minute
                )
                hd_end_date = Date.create(
                    year=end_date.year,
                    month=end_date.month,
                    day=end_date.day,
                    hour=hour,
                    minute=minute
                )

            except Exception as e:
                logger.error("ERROR: company_id, start_date and end_date are required")
                raise e

            logger.debug(f"Starting command to create new account snapshots "
                        f"for company={company_id} from {hd_start_date} to {hd_end_date}")

            company = Company.objects.get(pk=company_id)
            if company.status != Company.CompanyStatus.ACTIVE:
                raise Exception(f"Company (ID:{company_id}) is not active.")

            service = AccountSnapshotsService()
            service.create_new_snapshots_for_company(
                company=company,
                start_date=hd_start_date,
                end_date=hd_end_date,
                hour=hour,
                minute=minute
            )
            logger.debug(f"Finished command to create new account snapshots for company={company_id}")
            logging.debug("Command executed successfully!")
        except Exception as ex:
            logging.error(ex)
            raise Exception(ex)
