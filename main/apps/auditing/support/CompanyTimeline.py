import bisect
from typing import Optional, Dict, List, Iterable

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account
from main.apps.currency.models import FxPair
from main.apps.hedge.models import CompanyHedgeAction, FxPosition, AccountHedgeRequest, OMSOrderRequest, CompanyEvent

import logging

logger = logging.getLogger(__name__)


class PlotPoint:
    def __init__(self, time: Date,
                 company_event: Optional[CompanyEvent] = None):
        self.reference_time = time
        self.company_event = company_event
        self.company_hedge_actions = []

        self.account_positions: Optional[Dict[Account, List[FxPosition]]] = None
        self.account_hedge_requests: Optional[Dict[Account, List[AccountHedgeRequest]]] = {}
        self.company_fx_positions: Optional[Dict[FxPair, float]] = None
        self.oms_requests: Optional[List['OMSOrderRequest']] = []


class CompanyTimeline:
    def __init__(self,
                 company: Company,
                 account_positions: Dict[CompanyEvent, Dict[Account, List[FxPosition]]],
                 account_hedge_requests: Dict[CompanyHedgeAction, Dict[Account, AccountHedgeRequest]],
                 company_fx_positions: Dict[CompanyEvent, Dict[FxPair, List[float]]],
                 oms_requests: Dict[Date, List['OMSOrderRequest']],
                 ):
        self.company = company

        self.plot: Dict[CompanyEvent, PlotPoint] = {}

        for event, positions in account_positions.items():
            point = self.plot.setdefault(event,
                                         PlotPoint(time=event.get_time(),
                                                   company_event=event))
            point.account_positions = positions

        for event, company_fx_positions in company_fx_positions.items():
            if event is None:
                logger.warning(f"Company fx positions are associated with a None company event.")
                continue
            if event.get_time() is None:
                logger.warning(f"Event time is none.")
                continue
            point = self.plot.setdefault(event, PlotPoint(time=event.get_time()))
            point.company_event = event
            point.company_fx_positions = company_fx_positions

        # All events are set. Decide what requests go with which events.
        # Since the order of EOD is FIRST you take a company snapshot via reconciliation THEN you submit requests
        # (which may be given the same time stamp), we include all events [t_last, t_current) with an event at
        # t_current

        if len(self.plot) == 0:
            return  # Nothing we can do.

        # Create timeline of events, so we can efficiently search.
        event_pairs = list(sorted([(event.time, plot_point) for event, plot_point in self.plot.items()],
                                  key=lambda x: x[0]))
        event_times, ordered_events = list(zip(*event_pairs))

        for action, account_hedge_requests in account_hedge_requests.items():
            i = bisect.bisect_left(event_times, action.time)
            # Since hedging occurs after the reconciliation (at the same reference time), increment i if the times
            # are the same.
            if event_times[i] == action.time:
                i += 1
            if i == len(event_times):
                logger.debug(f"Account hedge request made after the last reconciliation?")
                continue
            ordered_events[i].company_hedge_actions.append(action)
            ordered_events[i].account_hedge_requests = {**ordered_events[i].account_hedge_requests,
                                                        **account_hedge_requests}

        for time, requests in oms_requests.items():
            i = bisect.bisect_left(event_times, time)
            # Since hedging occurs after the reconciliation (at the same reference time), increment i if the times
            # are the same.
            if event_times[i] == time:
                i += 1
            if i == len(event_times):
                logger.debug(f"Account hedge request made after the last reconciliation?")
                continue
            ordered_events[i].oms_requests += requests

        # Sort events by time.
        self.plot = {x: y for x, y in sorted(self.plot.items(), key=lambda x: x[0].time)}

        # Carry forward account positions, so they are set at each company event for which they are valid.
        last_account_positions = None
        for event, plot_point in self.plot.items():
            if not event.has_account_fx_snapshot:
                plot_point.account_positions = last_account_positions
            else:
                last_account_positions = plot_point.account_positions

    def get_all_plot_point_times(self) -> Iterable:
        return sorted(self.plot.keys())
