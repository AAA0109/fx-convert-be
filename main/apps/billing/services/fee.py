from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.DateTime.Date import Date
from main.apps.account.models import CashFlow

from main.apps.billing.models.payment import Payment
from main.apps.account.models.company import Company
from main.apps.billing.models.fee import Fee

from typing import List, Union, Optional, Sequence, Tuple, Iterable, Dict

import logging

logger = logging.getLogger(__name__)


class FeeProviderService(object):
    """
    Service responsible for information related to Pangea Fees, as well as an interface to add fees for a customer
    """
    dc = DayCounter_HD()

    def __init__(self):
        pass

    def get_fees(self,
                 company: Optional[Company] = None,
                 by_status: Optional[Iterable[Fee.Status]] = None,
                 by_type: Optional[Iterable[Fee.FeeType]] = None,
                 incurred_start: Optional[Date] = None,
                 incurred_end: Optional[Date] = None,
                 payment: Optional[Payment] = None,
                 due_on_or_before: Optional[Date] = None,
                 cashflow: Optional[CashFlow] = None) -> Sequence['Fee']:
        """
        Get fee objects based on filters
        :param company: Company, the company that these fees are attached to
        :param by_status: iterable of Status (optional), if supplied only retrieve fees matching supplied statuses
        :param by_type: iterable of FeeType (optional), if supplied only retrieve fees matching supplied fee types
        :param incurred_start: Date (optional), if supplied, ignore all fees incured strictly BEFORE this date
        :param incurred_end:  Date (optional), if supplied, ignore all fees incured strictly AFTER this date
        :param due_on_or_before: Date (optional), if supplied, ingnore all fees due strictly AFTER this date
        :param payment: Payment, the payment used to settle the fees
        :return: iterable of Fee objects
        """
        filters = {}
        if company:
            filters["company"] = company
        if by_status:
            filters["status__in"] = by_status
        if by_type:
            filters["fee_type__in"] = by_type
        if incurred_start:
            filters["incurred__gte"] = incurred_start
        if incurred_end:
            filters["incurred__lte"] = incurred_end
        if due_on_or_before:
            filters["due__lte"] = due_on_or_before
        if payment:
            filters["payment"] = payment
        if cashflow:
            filters["cashflow"] = cashflow

        return Fee.objects.filter(**filters)

    def get_fees_for_company(self,
                             company: Company,
                             incurred_start: Optional[Date] = None) -> Sequence[Fee]:
        """
        Get all fees for a company, from some first incurred date until present
        :param company: Company, the company that these fees are attached to
        :param incurred_start: Date (optional), if supplied, ignore all fees incured strictly BEFORE this date
        :return: sequence of Fee objects
        """
        return self.get_fees(company=company, incurred_start=incurred_start)

    def get_unpaid_maintenance_fees(self,
                                    company: Company,
                                    due_on_or_before: Date) -> Sequence['Fee']:
        """
        Get all unpaid maintenance fees for a company, that are due on or before a given date
        :param company: Company, the company that these fees are attached to
        :param due_on_or_before: Date (optional), if supplied, ingnore all fees due strictly AFTER this date
        :return: sequence of Fee objects
        """
        return self.get_fees(company=company,
                             by_status=(Fee.Status.DUE,),
                             due_on_or_before=due_on_or_before)

    def aggregate_fees_over_period(
        self,
        company: Company,
        by_status: Optional[Iterable[Fee.Status]] = None,
        by_type: Optional[Iterable[Fee.FeeType]] = None,
        incurred_start: Optional[Date] = None,
        incurred_end: Optional[Date] = None) -> float:
        """
        Aggregate (sum) all fees incured by a company over some period of time
        :param company: Company, the company that these fees are attached to
        :param by_status: iterable of Status (optional), if supplied only retrieve fees matching supplied statuses
        :param by_type: iterable of FeeType (optional), if supplied only retrieve fees matching supplied fee types
        :param incurred_start: Date (optional), if supplied, ignore all fees incured strictly BEFORE this date
        :param incurred_end:  Date (optional), if supplied, ignore all fees incured strictly AFTER this date
        :return: sum of all fees incurred over the time frame matching the supplied filters
        """
        fees = self.get_fees(company=company, by_status=by_status, by_type=by_type,
                             incurred_start=incurred_start, incurred_end=incurred_end)
        aggregate = 0
        for fee in fees:
            aggregate += fee.amount

        return aggregate
