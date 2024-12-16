from typing import Dict, Tuple, Optional

from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date


logger = get_logger(level=logging.INFO)


def get_times_for_day(company_id, day) -> Optional[Tuple[Date, Date]]:
    from main.apps.hedge.models import CompanyEvent

    objs = CompanyEvent.get_events_in_range(company=company_id,
                                            start_time=day.start_of_day(),
                                            end_time=day.start_of_next_day())
    if not objs:
        return None
    objs = list(objs)
    if len(objs) == 2:
        return Date.from_datetime(objs[0].time), Date.from_datetime(objs[1].time)
    return None


def run_by_event_id(event_id: int):
    from main.apps.hedge.models.company_event import CompanyEvent
    from main.apps.hedge.models import CompanyFxPosition

    event = CompanyEvent.objects.get(id=event_id)
    if not event:
        logger.error(f"Could not find event with id {event_id}.")
        return

    logger.debug(f"Running back in time...")
    starting_event = CompanyEvent.get_event_of_most_recent_positions(company=event.company,
                                                                     time=event.time,
                                                                     inclusive=False)
    logger.debug(f"Ending event is {event_id} at time {event.time}. "
                f"Starting event is {starting_event.id} at time {starting_event.time}")

    run_from_events(end_event=event)


def run_from_end_time(company_id: int, end_time: Date):
    from main.apps.account.models import Company
    from main.apps.hedge.models import CompanyEvent

    company = Company.get_company(company_id)
    ending_event = CompanyEvent.get_event_of_most_recent_positions(company=company, time=end_time, inclusive=True)
    starting_event = CompanyEvent.get_event_of_most_recent_positions(company=company, time=end_time,
                                                                     inclusive=False)

    run_from_events(end_event=ending_event)


def run_from_events(end_event):
    from main.apps.hedge.models import AccountHedgeRequest
    from main.apps.account.models import Company
    from main.apps.hedge.models import CompanyEvent
    from main.apps.hedge.services.broker_reconcile import ReconciliationCallback, BrokerReconcileService
    from main.apps.hedge.support.account_hedge_interfaces import AccountHedgeResultInterface
    from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

    class CheckReconciliationCallback(ReconciliationCallback):
        """
        The standard reconciliation callback, for use during normal operations. Actually creates company events and company
        FX positions.
        """

        def update_hedge_result(self,
                                result: AccountHedgeResultInterface,
                                status: AccountHedgeRequest.OrderStatus = AccountHedgeRequest.OrderStatus.CLOSED):
            return

        def create_company_positions(self, company: Company, time: Date, spot_cache: SpotFxCache) -> CompanyEvent:
            event = CompanyEvent.get_event_of_most_recent_positions(company=company, time=time, inclusive=True)

            logger.debug(f"Company event at time {time} was id = {end_event}, positions event is {event.id}.")
            return event

        def create_reconciliation_records(self, company: Company, time: Date, reconciliation_data, is_live: bool):
            logger.debug(f"Not creating any reconciliation record since this is just a check.")

        def create_fx_positions(self, final_positions_by_fxpair, company_event: CompanyEvent):
            logger.debug(f"During a real run, the following Fx positions would be created for event {company_event}:")
            for fxpair, positions_by_account in final_positions_by_fxpair.items():
                for account, position in positions_by_account.items():
                    logger.debug(f"  * Fx = {fxpair}, Account = {account}: {position.get_amount()}")

    if not end_event.has_company_fx_snapshot and not end_event.has_account_fx_snapshot:
        logger.error(f"Event does not have company or account FX snapshot, "
                     f"there was no reconciliation associated with this event")
        return

    end_time = end_event.time
    spot_cache = FxSpotProvider().get_spot_cache(time=end_time)

    reconciliation = BrokerReconcileService()
    reconciliation.reconcile_company(time=end_time, company=end_event.company, spot_cache=spot_cache,
                                     callback=CheckReconciliationCallback())


if __name__ == '__main__':
    import os, sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run_by_event_id(492)  # 495
