from django.db import transaction
from hdlib.AppUtils.log_util import logging
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company, AccountTypes, Account
from main.apps.broker.models import Broker
from main.apps.currency.models import Currency
from main.apps.hedge.services.cost import CostProviderService
from main.apps.history.models import AccountSnapshot
from main.apps.history.services.snapshot import SnapshotCreatorService
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.marketdata.services.universe_provider import UniverseProviderService

logger = logging.getLogger(__name__)


class AccountSnapshotsService:
    def create_new_snapshots_for_company(
        self,
        company: Company,
        start_date: Date,
        end_date: Date,
        hour: int = 13,
        minute: int = 0):
        """
        Create all new snapshots for a company.
        """
        company = Company.get_company(company)
        accounts = Account.get_active_accounts(
            live_only=True,
            company=company
        )

        logger.debug(f"Found {len(accounts)} active accounts for {company.name}")

        if len(accounts) <= 0:
            return

        for account in accounts:
            logger.debug(f"Creating snapshots for {account.name}")

            self.create_new_snapshots(
                account=account,
                start_date=start_date,
                end_date=end_date,
                hour=hour,
                minute=minute
            )

    def redo_snapshots_for_account(self, account: AccountTypes):
        account = Account.get_account(account)
        all_snapshots = AccountSnapshot.objects.filter(account=account).order_by('snapshot_time')
        logger.debug(f"Found {len(all_snapshots)} snapshots with some issues.")

        if len(all_snapshots) <= 0:
            return

        spot_caches = {}
        universe_provider_service = UniverseProviderService()
        domestics = {account.company.currency}

        for snapshot in all_snapshots:
            logger.debug(f"Handling account {account}.")
            time = Date.to_date(snapshot.snapshot_time)

            if time not in spot_caches:
                spot_cache = FxSpotProvider().get_spot_cache(time=time)
                spot_caches[time] = spot_cache
            else:
                spot_cache = spot_caches[time]

            universes = universe_provider_service.make_cntr_currency_universes_by_domestic(
                domestics=domestics,
                ref_date=time,
                bypass_errors=True,
                spot_fx_cache=spot_cache,
                all_or_none=False
            )

            brokers = Broker.objects.all()
            rates_caches = CostProviderService().create_all_rates_caches(time=time, brokers=brokers)
            snapshot_creator = SnapshotCreatorService(universes=universes, rates_caches=rates_caches)
            new_snapshot = snapshot_creator.create_account_snapshot(
                account=account,
                overwrite_next_in_last=False,
                do_save=False
            )
            self._replace_snapshot(old_snapshot=snapshot, new_snapshot=new_snapshot)
            self._relink_snapshot(new_snapshot=new_snapshot)
            logger.debug("================================================================")

    def redo_snapshots_for_company(self, company: Company):
        """
        Redo all snapshots for a company.
        """
        company = Company.get_company(company)
        all_snapshots = AccountSnapshot.objects.filter(account__company=company)

        logger.debug(f"Found {len(all_snapshots)} snapshots with some issues.")

        if len(all_snapshots) <= 0:
            return

        snapshots_by_date_by_account = {}
        for snapshot in sorted(all_snapshots, key=lambda x: x.snapshot_time):
            snapshots_by_date_by_account.setdefault(snapshot.account, {})[
                Date.to_date(snapshot.snapshot_time)] = snapshot

        spot_caches = {}
        universe_provider_service = UniverseProviderService()

        # TODO: get domestics dynamically
        domestics = {Currency.get_currency("USD")}
        for it, (account, snapshots) in enumerate(snapshots_by_date_by_account.items()):
            logger.debug(f"Handling account {it + 1} / {len(snapshots_by_date_by_account)} - {account}.")

            for i, (time, snapshot) in enumerate(snapshots.items()):
                logger.debug(f"Recalculating snapshot {i + 1} / {len(snapshots)}, time is {time}.")

                # Recalculate.
                if time not in spot_caches:
                    spot_cache = FxSpotProvider().get_spot_cache(time=time)
                    spot_caches[time] = spot_cache
                else:
                    spot_cache = spot_caches[time]

                universes = universe_provider_service.make_cntr_currency_universes_by_domestic(
                    domestics=domestics, ref_date=time, bypass_errors=True, spot_fx_cache=spot_cache,
                    all_or_none=False)

                # FUTURE IMPROVEMENT: just get the broker for the account
                brokers = Broker.objects.all()
                rates_caches = CostProviderService().create_all_rates_caches(time=time, brokers=brokers)
                snapshot_creator = SnapshotCreatorService(universes=universes, rates_caches=rates_caches)
                # Create, but do not save, the snapshot.
                new_snapshot = snapshot_creator.create_account_snapshot(account=account,
                                                                        overwrite_next_in_last=False,
                                                                        do_save=False)

                # Delete old snapshot and save the new snapshot (atomic transaction).
                # Also update the last-snapshot of the new snapshot so it points to the new snapshot.
                self._replace_snapshot(old_snapshot=snapshot, new_snapshot=new_snapshot)
                self._relink_snapshot(new_snapshot=new_snapshot)

                logger.debug("================================================================")

    @staticmethod
    def create_new_snapshots(account: AccountTypes,
                             start_date: Date,
                             end_date: Date,
                             hour: int = 13,
                             minute: int = 0):
        """
        Create a new snapshot for an account on every day between start_date and end_date, inclusively.
        Creates each snapshot at a standard time, 13:00 UTC by default.
        """
        logger.debug(f"Creating new snapshots for account {account} between {start_date} and {end_date}.")
        account = Account.get_account(account)
        if not account:
            logger.error(f"Could not find account.")

        universe_provider_service = UniverseProviderService()

        domestics = {account.company.currency}

        # Set the times, making sure the hours and minute are as chosen.
        date = Date.create(year=start_date.year, month=start_date.month, day=start_date.day, hour=hour, minute=minute)
        end_date = Date.create(year=end_date.year, month=end_date.month, day=end_date.day, hour=hour, minute=minute)

        while date <= end_date:
            logger.debug(f"Creating new snapshot for {account} on {date}.")
            spot_cache = FxSpotProvider().get_spot_cache(time=date)

            universes = universe_provider_service.make_cntr_currency_universes_by_domestic(
                domestics=domestics, ref_date=date, bypass_errors=True, spot_fx_cache=spot_cache,
                all_or_none=False)

            brokers = Broker.objects.all()
            rates_caches = CostProviderService().create_all_rates_caches(time=date, brokers=brokers)
            snapshot_creator = SnapshotCreatorService(universes=universes, rates_caches=rates_caches)
            # Create and save the snapshot.
            new_snapshot = snapshot_creator.create_account_snapshot(account=account,
                                                                    overwrite_next_in_last=False,
                                                                    do_save=True)
            logger.debug(f"Created new snapshot {new_snapshot} for {account} on {date}.")

            # Advance the date.
            date = date + 1

    @transaction.atomic
    def _replace_snapshot(self, old_snapshot: AccountSnapshot, new_snapshot: AccountSnapshot):
        """
        Replace an 'old' snapshot with a new snapshot, being careful not to delete the entire chain of snapshots.
        """
        # We have to "decouple" the old snapshot before we delete it, otherwise, the delete will propagate and
        # get rid of all snapshots.
        try:
            last = old_snapshot.last_snapshot
        except Exception:
            last = None
        try:
            next = old_snapshot.next_snapshot
        except Exception:
            next = None
        old_snapshot.last_snapshot = None
        old_snapshot.next_snapshot = None

        if last:
            last.next_snapshot = None
            last.save()
        if next:
            next.last_snapshot = None
            next.save()
        old_snapshot.delete()

        new_snapshot.save()

    @transaction.atomic
    def _relink_snapshot(self, new_snapshot):
        last = new_snapshot.last_snapshot
        next = new_snapshot.next_snapshot
        if last:
            last.next_snapshot = new_snapshot
            last.save()
        if next:
            next.last_snapshot = new_snapshot
            next.save()
