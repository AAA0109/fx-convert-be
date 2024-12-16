from typing import List, Optional, Iterable

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account, CompanyTypes, AccountTypes
from main.apps.auditing.services.auditing import AuditingService
from main.apps.history.models import AccountSnapshot

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


class DataFixingService:
    """
    Service that can correct different types of data, e.g. redo snapshots, reconciliations, etc.
    """

    @staticmethod
    def remake_account_snapshots(snapshots: Iterable[AccountSnapshot]):
        for it, snapshot in enumerate(snapshots):
            account = snapshot.account
            time = Date.from_datetime(snapshot.snapshot_time)

            logger.debug(f"Remaking snapshot {it}: for account {account}, reference time {time}.")

            snapshot.delete()
            # Create a new snapshot
            service = AuditingService.create_snapshot_creator_for_time(time=time)
            service.create_account_snapshot(account=account, overwrite_next_in_last=True)

    @staticmethod
    def remake_snapshots(company: Optional[CompanyTypes] = None,
                         account: Optional[AccountTypes] = None,
                         start_time: Optional[Date] = None,
                         end_time: Optional[Date] = None):
        snapshots = AccountSnapshot.get_snapshots(company=company, account=account,
                                                  start_time=start_time, end_time=end_time)
        DataFixingService.remake_account_snapshots(snapshots=snapshots)
