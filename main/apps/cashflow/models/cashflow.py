import logging
import uuid
from typing import Optional, Union, Iterable

from django.db import models
from django.utils.translation import gettext_lazy as __
from django_extensions.db.models import TimeStampedModel
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company
from main.apps.core.constants import LOCK_SIDE_HELP_TEXT
from main.apps.currency.models.currency import Currency, CurrencyId
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.models.ticket import Ticket
from main.apps.util import get_or_none

logger = logging.getLogger(__name__)


class SingleCashFlow(TimeStampedModel):
    """
    Model for a single payment cashflow.

    A cashflow represents a single coupon payment in a specific currency on a specific date.
    A positive amount is a payment, and a negative amount is a receipt.

    The cashflow is associated with a single company.
    """

    cashflow_id = models.UUIDField(default=uuid.uuid4, help_text="The unique ID of the cashflow", editable=False)

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="cashflows", null=False)

    # the cashflow generator that is used to generate this single cashflow
    generator = models.ForeignKey('cashflow.CashFlowGenerator', on_delete=models.PROTECT, related_name="cashflows",
                                  null=True,
                                  blank=True)

    class Status(models.TextChoices):
        DRAFT = "draft", __("DRAFT")
        PENDING = "pending", __("PENDING")
        APPROVED = "approved", __("APPROVED")
        LIVE = "live", __("LIVE")
        CANCELED = "canceled", __("CANCELED")

    status = models.CharField(max_length=24,
                              default=Status.DRAFT,
                              choices=Status.choices,
                              help_text="The status of the cashflow")

    # ========================================================================================
    #  Cashflow definition
    # ========================================================================================

    # The pay date of the cashflow, when its received/paid
    pay_date = models.DateTimeField(
        help_text="The date the cashflow is paid or received",
        null=False
    )

    # Buy currency of the cashflow
    buy_currency = models.ForeignKey(Currency,
                                     on_delete=models.PROTECT,
                                     related_name='%(class)s_buy_currency',
                                     null=True,
                                     help_text="The buy currency of the cashflow")

    # Sell currency of the cashflow
    sell_currency = models.ForeignKey(Currency,
                                      on_delete=models.PROTECT,
                                      related_name='%(class)s_sell_currency',
                                      null=True,
                                      help_text="The currency of the cashflow")

    # The side the currency is locked to
    lock_side = models.ForeignKey(Currency, on_delete=models.PROTECT,
                                  related_name='%(class)s_lock_side',
                                  null=True,
                                  blank=True,
                                  help_text=LOCK_SIDE_HELP_TEXT)

    # Amount of the cashflow in its lock side currency
    amount = models.FloatField(null=False, help_text="The amount of the cashflow")

    # Amount of the cashflow in counter currency
    cntr_amount = models.FloatField(null=True, help_text="The counter amount of the cashflow")

    # ========================================================================================
    # Additional information
    # ========================================================================================
    name = models.CharField(max_length=255, null=True, blank=True, help_text="A name for the cashflow")
    description = models.TextField(null=True, blank=True, help_text="A description of the cashflow")
    ticket_id = models.UUIDField(null=True, blank=True, help_text="the ticket ID associated with this single cashflow")
    tickets = models.ManyToManyField(Ticket, blank=True)
    transaction_date = models.DateField(null=True, blank=True, help_text="Payment's cashflow transaction date")

    @staticmethod
    def get_cashflow_object(
        company: Union[int, Company],
        start_date: Date,
        exclude_unknown_on_ref_date: bool = False,
        currencies: Iterable[Union[CurrencyId, Currency]] = None,
    ) -> Iterable["SingleCashFlow"]:
        """
        Get "active" cashflows for a company, ie those that have not already been paid
        :param company: Company, the company to get cashflows for
        :param start_date: Date, the reference date (only cashflows occurring on or after this date are considered)
        :param exclude_unknown_on_ref_date: bool, if true, exclude all cashflows that were not created by the ref_date,
            this flag is for historical testing / reporting purposes, since hedges only knew cashflows that existed
            at the time of the hedge
        :param currencies: Iterable of currency ids or objects (optional), if supplied only return matching currencies
        :return: iterable of CashFlow objects
        """
        # TODO: Separate the date range, start_date, max_days_away, and the reference date, which is used to filter
        #   with created__lte.

        filters = {}

        if exclude_unknown_on_ref_date:
            filters["created__lte"] = start_date

        if currencies is not None:
            filters["currency__in"] = currencies

        filters["status__in"] = [
            SingleCashFlow.Status.LIVE,
        ]
        filters['pay_date__gte'] = start_date

        return SingleCashFlow.objects.filter(**filters).order_by("date")

    @staticmethod
    @get_or_none
    def get_cashflow(cashflow_id: int) -> 'SingleCashFlow':
        return SingleCashFlow.objects.get(pk=cashflow_id)

    @staticmethod
    @get_or_none
    def get_cashflows(cashflow_ids: Iterable[int]) -> Iterable['SingleCashFlow']:
        return SingleCashFlow.objects.filter(id__in=cashflow_ids)

    def get_market_name(self) -> str:
        return FxPair(
            base_currency=self.sell_currency,
            quote_currency=self.buy_currency
        ).market

    @property
    def related_ticket(self) -> Optional[Ticket]:
        if 'tickets' in self._prefetched_objects_cache:
            tickets = list(self._prefetched_objects_cache['tickets'])
            if tickets:
                return tickets[0]
        elif self.tickets.count() > 0:
            return self.tickets.first()
        else:
            try:
                return Ticket.objects.get(pk=self.ticket_id)
            except Ticket.DoesNotExist:
                return None
        return None
