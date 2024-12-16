from typing import List

import numpy as np

from hdlib.DateTime.Date import Date

# Logging.
from hdlib.AppUtils.log_util import get_logger, logging
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)


def run():
    from main.apps.history.models import AccountSnapshot

    snapshots_issues = AccountSnapshot.objects.filter(account__company=18)
    # snapshots_issues = AccountSnapshot.objects.filter(account__in=(261, 262))
    # snapshots_issues = [AccountSnapshot.objects.get(pk=5131), AccountSnapshot.objects.get(pk=5211), AccountSnapshot.objects.get(pk=5329)]
    logger.debug(f"Found {len(snapshots_issues)} snapshots with some issues.")

    redo_snapshots(snapshots_issues=snapshots_issues)


def redo_snapshots(snapshots_issues):
    from main.apps.history.models import AccountSnapshot
    from main.apps.history.services.snapshot import SnapshotCreatorService
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from main.apps.currency.models import Currency
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.account.models import Broker
    from main.apps.hedge.services.cost import CostProviderService
    from django.db import transaction

    @transaction.atomic
    def replace_snapshot(old_snapshot: AccountSnapshot, new_snapshot: AccountSnapshot):
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

        # new_snapshot.last_snapshot = last
        # new_snapshot.next_snapshot = next
        new_snapshot.save()

    @transaction.atomic
    def relink_snapshot(new_snapshot):
        last = new_snapshot.last_snapshot
        next = new_snapshot.next_snapshot
        if last:
            last.next_snapshot = new_snapshot
            last.save()
        if next:
            next.last_snapshot = new_snapshot
            next.save()

    snapshots_by_date_by_account = {}
    for snapshot in sorted(snapshots_issues, key=lambda x: x.snapshot_time):
        snapshots_by_date_by_account.setdefault(snapshot.account, {})[Date.to_date(snapshot.snapshot_time)] = snapshot

    spot_caches = {}
    universe_provider_service = UniverseProviderService()

    domestics = {Currency.get_currency("USD")}
    for it, (account, snapshots) in enumerate(snapshots_by_date_by_account.items()):
        logger.debug(f"Handling account {it + 1} / {len(snapshots_by_date_by_account)} - {account}.")

        times: List[Date] = [Date.to_date(d) for d in sorted(snapshots.keys())]
        fmt_times = [str(d) for d in times]

        for i, (time, snapshot) in enumerate(snapshots.items()):
            logger.debug(f"Recalculating snapshot {i + 1} / {len(snapshots)}, time is {time}.")

            # Recalculate.
            if time not in spot_caches:
                spot_cache = FxSpotProvider().get_spot_cache(time=time)
                spot_caches[time] = spot_cache
            else:
                spot_cache = spot_caches[time]

            universes = universe_provider_service.make_cntr_currency_universes_by_domestic(
                domestics=domestics, ref_date=time, bypass_errors=True, spot_fx_cache=spot_cache, all_or_none=False)

            # FUTURE IMPROVEMENT: just get the broker for the account
            brokers = Broker.objects.all()
            rates_caches = CostProviderService().create_all_rates_caches(time=time, brokers=brokers)
            snapshot_creator = SnapshotCreatorService(universes=universes, rates_caches=rates_caches)
            # Create, but do not save, the snapshot.

            # snapshot.delete()
            # new_snapshot = snapshot_creator.create_account_snapshot(account=account)

            new_snapshot = snapshot_creator.create_account_snapshot(account=account,
                                                                    overwrite_next_in_last=False,
                                                                    do_save=False)

            # Delete old snapshot and save the new snapshot (atomic transaction). Also update the last-snapshot of the
            # new snapshot so it points to the new snapshot.
            replace_snapshot(old_snapshot=snapshot, new_snapshot=new_snapshot)
            relink_snapshot(new_snapshot=new_snapshot)

            logger.debug("================================================================")


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
