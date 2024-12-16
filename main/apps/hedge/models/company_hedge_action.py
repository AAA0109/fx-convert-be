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

CompanyHedgeActionId = int


class CompanyHedgeAction(models.Model):
    """
    Hedge action identifies a change to some or all hedge positions. This action will have an associated set of trades,
    ie changes in the hedge positions for each fx pair

    This entry is primarily something that many tables point back to in a many-to-one manner,
    so it does not have many entries of its own.
    """

    # TODO: Make (company, time) unique together.

    # The company whose action this is.
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False)

    # The time at which this action was created.
    time = models.DateTimeField(null=False)

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

    @staticmethod
    def get_action(company_hedge_action: Union['CompanyHedgeAction', CompanyHedgeActionId]):
        if isinstance(company_hedge_action, CompanyHedgeAction):
            return company_hedge_action
        elif isinstance(company_hedge_action, CompanyHedgeActionId):
            return CompanyHedgeAction.objects.get(id=company_hedge_action)
        raise ValueError(f"did not recognize type of company_hedge_action: {company_hedge_action}")

    @staticmethod
    def get_actions(company: CompanyTypes,
                    start_time: Optional[Date] = None,
                    end_time: Optional[Date] = None) -> Iterable['CompanyHedgeAction']:
        company_ = Company.get_company(company)
        if not company_:
            raise ValueError(f"could not find company from input {company}")
        filters = {"company": company_}
        if start_time is not None:
            filters["time__gte"] = start_time
        if end_time is not None:
            filters["time__lt"] = end_time
        return CompanyHedgeAction.objects.filter(**filters)

    # ================================================================================
    #  Mutators.
    # ================================================================================

    @staticmethod
    def add_company_hedge_action(company: CompanyTypes,
                                 time: Optional[Date] = None
                                 ) -> Tuple[ActionStatus, Optional['CompanyHedgeAction']]:
        company_ = Company.get_company(company)
        if company_ is None:
            return ActionStatus.error(f"could not find customer {company}"), None
        try:
            args = {"company": company_, "time": time if time else Date.now()}
            action = CompanyHedgeAction.objects.create(**args)
            return ActionStatus.success(), action
        except Exception as ex:
            return ActionStatus.error(f"could not add company hedge action: {ex}"), None

    @staticmethod
    def get_latest_company_hedge_action(company: CompanyTypes,
                                        time: Optional[Date] = None,
                                        inclusive: bool = True) -> Optional['CompanyHedgeAction']:
        filters = {"company": company}
        if time:
            filters["time__lte" if inclusive else "time__lt"] = time
        qs = CompanyHedgeAction.objects.filter(**filters).order_by("-time")
        return qs.first() if qs else None


CompanyHedgeActionTypes = Union[CompanyHedgeAction, CompanyHedgeActionId]

auditlog.register(CompanyHedgeAction)
