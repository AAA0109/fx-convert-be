import logging
from hdlib.DateTime.Date import Date
from django.core.management.base import BaseCommand

from main.apps.account.models.cashflow import CashFlow
from main.apps.account.services.snapshot import AccountSnapshotsService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Django command to recreate snapshots given a cashflow"

    def add_arguments(self, parser):
        parser.add_argument('--cashflow_ids', nargs='+', type=int, help="Required: command delimited Cashflow IDs")

    def handle(self, *args, **options):
        cashflow_ids = options["cashflow_ids"]
        for cashflow_id in cashflow_ids:
            try:
                logger.debug(f"recreating snapshots for cashflow: {cashflow_id}")
                cashflow = CashFlow.objects.get(pk=cashflow_id)
                account = cashflow.account
                snapshots = cashflow.account.accountsnapshot_set.all()

                start_date = cashflow.created
                end_date = Date.today()
                if end_date > cashflow.date:
                    end_date = cashflow.date

                hdl_start_date = Date.create(
                    year=start_date.year,
                    month=start_date.month,
                    day=start_date.day,
                    hour=start_date.hour,
                    minute=start_date.minute
                )

                hdl_end_date = Date.create(
                    year=end_date.year,
                    month=end_date.month,
                    day=end_date.day,
                    hour=end_date.hour,
                    minute=end_date.minute
                )

                logger.debug(f"Deleting snapshots for account: {account.pk}")
                snapshots.delete()

                logger.debug(f"Recreating snapshots for account: {account.pk}")
                snapshot_service = AccountSnapshotsService()
                snapshot_service.create_new_snapshots(account=account, start_date=hdl_start_date,
                                                      end_date=hdl_end_date)
                logger.debug(f"Redoing snapshots for account: {account.pk}")
                snapshot_service.redo_snapshots_for_account(account)

            except CashFlow.DoesNotExist:
                logger.error(f"CashFlow with ID {cashflow_id} does not exist")
            except Exception as e:
                logger.error(f"Unable to recreate snapshot for cashflow: {e}")
