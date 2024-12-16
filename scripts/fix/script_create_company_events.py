"""
This script finds all CompanyHedgeActions and CompanyFxPositions and creates CompanyEvents for each of these
that do not already have a corresponding CompanyEvent.

Then, for each FxPosition, the CompanyEvent foreign key is set to point to the correct CompanyEvent.

"""

# Logging.
from typing import Dict, Tuple

import numpy as np

from hdlib.AppUtils.log_util import get_logger, logging
from hdlib.DateTime.Date import Date
from scripts.lib.only_local import only_allow_local

logger = get_logger(level=logging.INFO)


def clean_account_hedge_requests():
    """
    There are account hedge requests where the requested_amount is some very small random number. Clip these down
    to be zero instead.
    """
    from main.apps.hedge.models import AccountHedgeRequest

    for obj in AccountHedgeRequest.objects.all():
        if np.abs(obj.requested_amount) < 1e-2:
            obj.requested_amount = 0.
            obj.save()


def clean_fx_positions():
    """
    There are Fx positions where the requested_amount is some very small random number. Clip these down
    to be zero instead. If the amount is zero, make sure the total price is zero too.
    """
    from main.apps.hedge.models import FxPosition

    for pos in FxPosition.objects.all():
        if np.abs(pos.amount) < 1e-2:
            pos.amount = 0.
            pos.total_price = 0.
            pos.save()


# noinspection DuplicatedCode
def run():
    from main.apps.hedge.models import CompanyHedgeAction, CompanyEvent, FxPosition
    from main.apps.hedge.models.company_fxposition import CompanyFxPosition
    from main.apps.account.models import Company

    clean_account_hedge_requests()
    clean_fx_positions()

    # First, create CompanyEvents for every CompanyHedgeAction that does not have a corresponding event, and for every

    existing_events: Dict[Tuple[Company, Date], CompanyEvent] \
        = {(event.company, event.time): event for event in CompanyEvent.objects.all()}

    for position in CompanyFxPosition.objects.all():
        position.snapshot_event = None
        position.save()

    new_events = []
    for action in CompanyHedgeAction.objects.all():
        key = (action.company, action.time)
        if key not in existing_events:
            if action.time is None:
                logger.error(f"Time is None for company hedge action {action.id}")
                continue
            event = CompanyEvent(company=action.company, time=action.time)
            event.has_hedge_action = True
            existing_events[key] = event

            new_events.append(event)
        else:
            event = existing_events[key]
            if not event.has_hedge_action:
                event.has_hedge_action = True
                event.save()

    for position in CompanyFxPosition.objects.all():
        key = (position.company, position.record_time)
        if key not in existing_events:
            if position.record_time is None:
                logger.error(f"Time is None for company position {position.id}")
                continue
            event = CompanyEvent(company=position.company, time=position.record_time)
            event.has_company_fx_snapshot = True
            existing_events[key] = event

            new_events.append(event)
        else:
            event = existing_events[key]
            if not event.has_company_fx_snapshot:
                event.has_company_fx_snapshot = True
                event.save()

    logger.debug(f"Bulk creating {len(new_events)} company events.")
    CompanyEvent.objects.bulk_create(new_events)

    # Next, for each FxPosition, set the event to be the one corresponding to hedge actions.

    count = 0
    for fx_position in FxPosition.objects.all():
        if fx_position.company_event is None:
            company, time = fx_position.company_hedge_action.company, fx_position.company_hedge_action.time
            event = existing_events.get((company, time), None)
            if not event:
                # Find the event, which must have already existed.
                event = CompanyEvent.objects.filter(company=fx_position.company_hedge_action.company,
                                                    time=fx_position.company_hedge_action.time).first()
            event.has_account_fx_snapshot = True
            event.save()

            fx_position.company_event = event
            fx_position.save()

            count += 1
    logger.debug(f"Set events in {count} account Fx positions.")

    # For each CompanyFxPosition, set the event.

    count = 0
    for company_fx_position in CompanyFxPosition.objects.all():
        if company_fx_position.snapshot_event is None:
            event = existing_events.get((company_fx_position.company, company_fx_position.record_time), None)
            if event and (company_fx_position.snapshot_event is None or not event.has_company_fx_snapshot):
                event.has_company_fx_snapshot = True
                event.save()

                company_fx_position.snapshot_event = event
                company_fx_position.save()

                count += 1
            else:
                logger.warning(f"Could not find event for (company = {company_fx_position.company}, "
                               f"t = {company_fx_position.record_time}).")
    logger.debug(f"Set events in {count} company Fx positions.")


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    import os
    import sys

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
