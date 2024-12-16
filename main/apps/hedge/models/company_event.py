from datetime import datetime
from typing import Tuple, Optional, Union, Iterable

from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, CompanyTypes
from main.apps.marketdata.models import DataCut
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.util import ActionStatus, get_or_none

import logging

logger = logging.getLogger(__name__)

CompanyEventId = int


class CompanyEvent(models.Model):
    """
    Represents some event for a company, like taking a snapshot of positions.
    """

    # ================================================================================
    #  Model data.
    # ================================================================================

    # The company whose action this is.
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    # The time at which the event is located.
    time = models.DateTimeField(null=False)

    # ==============================
    #  Information about the event
    # ==============================

    # Whether there was hedging associated with this event.
    has_hedge_action = models.BooleanField(null=False, default=False)

    # Whether a company fx positions snapshot was associated with this event.
    has_company_fx_snapshot = models.BooleanField(null=False, default=False)

    # Whether an account fx positions snapshot was associated with this event.
    has_account_fx_snapshot = models.BooleanField(null=False, default=False)

    # ================================================================================
    #  Overridden functions.
    # ================================================================================

    def save(self, *args, **kwargs):
        """
        Override save so that if a date is not provided, the current date is used.
        Originally, time was set with auto_now_add=True, but for testing, we want to be able to specify dates in the
        past as the "time" at which the action was created.
        """
        if self.time is None:
            self.time = Date.now()
        super().save(*args, **kwargs)

    # ================================================================================
    #  Accessors.
    # ================================================================================

    def get_time(self) -> Date:
        """ Get the time as an hdlib Date """
        return Date.from_datetime(self.time)

    @staticmethod
    def get_action(company_event: Union['CompanyEvent', CompanyEventId]):
        if isinstance(company_event, CompanyEvent):
            return company_event
        elif isinstance(company_event, CompanyEventId):
            return CompanyEvent.objects.get(id=company_event)
        raise ValueError(f"did not recognize type of company_event: {company_event}")

    @staticmethod
    def get_events_in_range(company: CompanyTypes,
                            start_time: Optional[Date] = None,
                            end_time: Optional[Date] = None,
                            lower_inclusive: bool = True,
                            upper_inclusive: bool = True):
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)
        filters = {"company": company_}
        if start_time:
            filters["time__gte" if lower_inclusive else "time__gt"] = start_time
        if end_time:
            filters["time__lte" if upper_inclusive else "time__lt"] = end_time
        return CompanyEvent.objects.filter(**filters)

    @staticmethod
    def get_event_or_none(company: CompanyTypes,
                          time: Date):
        company_ = Company.get_company(company)
        if company_ is None:
            raise ValueError(f"could not find company for {company}")
        try:
            args = {"company": company_, "time": time if time else Date.now()}
            event = CompanyEvent.objects.get(**args)
            return event
        except Exception as ex:
            return None

    @staticmethod
    def get_latest_company_event(company: CompanyTypes,
                                 time: Optional[Date] = None) -> Optional['CompanyEvent']:
        filters = {"company": company}
        if time:
            filters["time__lte"] = time
        qs = CompanyEvent.objects.filter(**filters).order_by("-time")
        return qs.first() if qs else None

    @staticmethod
    def get_event_of_most_recent_positions(company: Company,
                                           time: Optional[Date] = None,
                                           inclusive: bool = True,
                                           check_account_positions: bool = False
                                           ):
        """
        Get the last company event at which time position snapshots were taken.

        Currently, during usual operation of the system, company and account snapshots are always taken together, so
        for every company event, has_account_fx_snapshot <=> has_company_fx_snapshot. By default, we only look for
        events where has_company_fx_snapshot is True. However, to accomodate potential changes in the future, you can
        set check_account_positions to True, and the query will check for check_account_positions = True.
        """
        filters = {"company": company}
        if check_account_positions:
            filters["has_account_fx_snapshot"] = True
        else:
            filters["has_company_fx_snapshot"] = True
        if time:
            filters["time__lte" if inclusive else "time__lt"] = time

        qs = CompanyEvent.objects.filter(**filters).order_by("-time")
        if not qs:
            return None
        return qs.first()

    # ================================================================================
    #  Mutators.
    # ================================================================================

    @staticmethod
    def get_or_create_event(company: CompanyTypes,
                            time: Optional[Date] = None
                            ) -> Optional['CompanyEvent']:
        company_ = Company.get_company(company)
        if company_ is None:
            raise ValueError(f"could not find company from {company}")
        try:
            args = {"company": company_, "time": time if time else Date.now()}
            event, _ = CompanyEvent.objects.get_or_create(**args)
            return event
        except Exception as ex:
            raise ValueError(f"could not add company hedge action: {ex}")


auditlog.register(CompanyEvent)
