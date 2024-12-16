from typing import Dict, Tuple, Optional

from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date


logger = get_logger(level=logging.INFO)


def check_snapshot_by_id(snapshot_id: int):
    from main.apps.history.models import AccountSnapshot
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from main.apps.currency.models import Currency
    from main.apps.account.models import Broker
    from main.apps.hedge.services.cost import CostProviderService
    from main.apps.history.services.snapshot import SnapshotCreatorService

    snapshot = AccountSnapshot.objects.get(pk=snapshot_id)
    time = Date.from_datetime(snapshot.snapshot_time)
    account = snapshot.account

    # FxSpotProvider().get_spot_cache(time=snapshot.snapshot_time)
    universe_provider_service = UniverseProviderService()

    usd = Currency.get_currency("USD")
    universe = universe_provider_service.make_cntr_currency_universe(
        domestic=usd, ref_date=time, bypass_errors=True)

    # FUTURE IMPROVEMENT: just get the broker for the account
    brokers = Broker.objects.all()
    rates_caches = CostProviderService().create_all_rates_caches(time=time, brokers=brokers)
    snapshot_creator = SnapshotCreatorService(universes={usd: universe}, rates_caches=rates_caches)
    return snapshot_creator.generate_snapshot(account=account)


if __name__ == '__main__':
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    check_snapshot_by_id(2063)
