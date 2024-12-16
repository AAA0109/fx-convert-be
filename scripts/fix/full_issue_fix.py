from typing import Dict, Tuple, Optional, List

from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date

logger = get_logger(level=logging.INFO)


def redo_reconciliations_in_range(company, start_time, end_time):
    from main.apps.hedge.services.broker_reconcile import ReconciliationCallback
    from main.apps.hedge.support.account_hedge_interfaces import AccountHedgeResultInterface
    from main.apps.hedge.models import AccountHedgeRequest
    from main.apps.hedge.services.broker_reconcile import BrokerReconcileService
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
    from main.apps.hedge.models import CompanyEvent, FxPosition
    from main.apps.account.models import Company

    class FixReconciliationCallback(ReconciliationCallback):
        """
        The standard reconciliation callback, for use during normal operations. Actually creates company events and company
        FX positions.
        """

        def __init__(self, event):
            self._event = event

        def update_hedge_result(self,
                                result: AccountHedgeResultInterface,
                                status: AccountHedgeRequest.OrderStatus = AccountHedgeRequest.OrderStatus.CLOSED):
            if isinstance(result, AccountHedgeRequest):
                result.save()

        def create_company_positions(self, company: Company, time: Date, spot_cache: SpotFxCache) -> CompanyEvent:

            event = CompanyEvent.get_event_of_most_recent_positions(company=company, time=time, inclusive=True)

            logger.debug(f"Company event at time {time} was id = {self._event.id}, positions event is {event.id}.")
            return self._event

        def create_reconciliation_records(self, company: Company, time: Date, reconciliation_data, is_live: bool):
            logger.debug(f"Not creating any reconciliation record since this is just a check.")

        def create_fx_positions(self, final_positions_by_fxpair, company_event: CompanyEvent):
            existing_positions = FxPosition.objects.filter(company_event=company_event)

            existing_positions_by_fxpair = {}
            for pos in existing_positions:
                existing_positions_by_fxpair.setdefault(pos.fxpair, {})[pos.account] = pos

            logger.debug(f"Existing positions: (event {company_event})")
            for pair, positions in sorted(existing_positions_by_fxpair.items(), key=lambda x: x[0]):
                logger.debug(f"{pair}:")
                for account, position in positions.items():
                    logger.debug(f"    >> {account}: {position.amount}, price = {position.total_price}")

            logger.debug(f"Positions from re-hedge: (event {company_event})")
            for pair, positions in sorted(final_positions_by_fxpair.items(), key=lambda x: x[0]):
                logger.debug(f"{pair}:")
                for account, position in positions.items():
                    logger.debug(f"    >> {account}: {position.amount}, price = {position.total_price}")

            if existing_positions:
                existing_positions.delete()

            broker_reconciliation_service = BrokerReconcileService()
            broker_reconciliation_service.create_fx_positions(final_positions_by_fxpair, company_event=company_event)

    intervening_events = CompanyEvent.get_events_in_range(company=company,
                                                          start_time=start_time,
                                                          end_time=end_time,
                                                          lower_inclusive=False)

    logger.debug(f"Redoing {len(intervening_events)} reconciliations.")
    for company_event in sorted(intervening_events, key=lambda x: x.time):
        if not company_event.has_account_fx_snapshot:
            logger.debug(f"Event {company_event.id} does not have company FX snapshot, "
                        f"not running reconciliation")
        else:
            logger.debug(f"Reconciliation for event {company_event.id}.")

        time = company_event.time

        spot_cache = FxSpotProvider().get_spot_cache(time=time)

        reconciliation = BrokerReconcileService()
        reconciliation.reconcile_company(time=time, company=company, spot_cache=spot_cache,
                                         callback=FixReconciliationCallback(company_event))


def correct_all(company):
    from main.apps.hedge.models import CompanyHedgeAction
    from main.apps.hedge.services.oms import OMSHedgeService
    from main.apps.hedge.services.cost import CostProviderService
    from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService
    from main.apps.account.models import Company
    from main.apps.hedge.services.hedger import hedge_company
    from main.apps.marketdata.services.universe_provider import UniverseProviderService
    from scripts.fix.lib.liquidity_fix_callback import LiquidityFixHedgeCallback

    all_actions = list(CompanyHedgeAction.get_actions(company=company))

    reconciliations_before = True
    reconciliations_after = True

    # =============================================================================================================
    #   Run the redo.
    # =============================================================================================================

    company = Company.get_company(company=company)
    domestic = company.currency

    if reconciliations_before:
        redo_reconciliations_in_range(company=company,
                                      start_time=None,
                                      end_time=all_actions[0].time)

    for it, company_hedge_action in enumerate(all_actions):
        hedge_time = Date.from_datetime(company_hedge_action.time)
        universe = UniverseProviderService().make_cntr_currency_universe(domestic=domestic, ref_date=hedge_time,
                                                                         bypass_errors=True)
        cost_provider = CostProviderService().get_cost_provider(date=hedge_time,
                                                                fx_cache=universe,
                                                                domestic=company.currency,
                                                                broker="IBKR")

        # =============================================================================================================
        #   Get all accounts and their current positions, cash exposures, and history providers for each of them.
        # =============================================================================================================

        # Get LIVE and DEMO accounts unless they failed.
        hedge_account_types = list(OMSHedgeService.hedgeable_account_types)
        # Create a callback object that creates account hedge requests.
        callback = LiquidityFixHedgeCallback(company_hedge_action=company_hedge_action)
        market_converter = FxMarketConventionService().make_fx_market_converter()

        hedge_company(hedge_time=hedge_time,
                      company_hedge_action=company_hedge_action,
                      cost_provider=cost_provider,
                      hedge_account_types=hedge_account_types,
                      market_converter=market_converter,
                      universe=universe,
                      callback=callback)

        # Redo reconciliations
        if it + 1 < len(all_actions):
            redo_reconciliations_in_range(company=company,
                                          start_time=company_hedge_action.time,
                                          end_time=all_actions[it + 1].time)

        elif reconciliations_after:
            redo_reconciliations_in_range(company=company,
                                          start_time=company_hedge_action.time,
                                          end_time=None)


def redo_snapshots_for_company(company):
    from main.apps.history.models import AccountSnapshot

    snapshots_issues = AccountSnapshot.objects.filter(account__company=company)
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
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    correct_all(company=18)
    redo_snapshots_for_company(company=18)
