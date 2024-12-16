import uuid
from datetime import date as pydate
from datetime import datetime
from typing import List, Optional, Union

import pytz
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from recurrence.fields import RecurrenceField

from main.apps.account.models import Company
from main.apps.account.models.user import User
from main.apps.approval.models.approval import ApprovalMethod, ApprovalTriggerMethod
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.core.constants import VALUE_DATE_HELP_TEXT, LOCK_SIDE_HELP_TEXT
from main.apps.currency.models import Currency
from main.apps.payment.services.recurrence_provider import RecurrenceProvider


class CashFlowGenerator(TimeStampedModel):
    """
    Model for a generating single payment cashflow.

    A cashflow represents a single coupon payment in a specific currency on a specific date.
    A positive amount is a payment, and a negative amount is a receipt.

    The cashflow is associated with a single company.
    """
    cashflow_id = models.UUIDField(default=uuid.uuid4, help_text="The unique ID of the cashflow", editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="cashflow_generators", null=False)

    # ========================================================================================
    #  Cashflow definition
    # ========================================================================================

    # The value date of the cashflow, when its received/paid
    value_date = models.DateField(
        null=True,
        help_text=VALUE_DATE_HELP_TEXT
    )

    # Buy currency of the cashflow
    buy_currency = models.ForeignKey(Currency,
                                     on_delete=models.PROTECT,
                                     related_name='%(class)s_from_currency',
                                     help_text="The from currency of the cashflow")

    # Sell currency of the cashflow
    sell_currency = models.ForeignKey(Currency,
                                      on_delete=models.PROTECT,
                                      related_name='%(class)s_to_currency',
                                      null=True,
                                      blank=True,
                                      help_text="The to currency of the cashflow")

    # The side the currency is locked to
    lock_side = models.ForeignKey(Currency, on_delete=models.PROTECT,
                                  related_name='%(class)s_lock_side',
                                  null=True,
                                  blank=True,
                                  help_text=LOCK_SIDE_HELP_TEXT)

    # Amount of the cashflow in its currency
    amount = models.FloatField(null=True, help_text="The amount of the cashflow")

    # Amount of the cashflow in counter currency
    cntr_amount = models.FloatField(null=True, help_text="The counter amount of the cashflow")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        LIVE = "live", _("Live")
        HEDGED = 'hedged', _("Hedged")
        SETTLED = 'settled', _("Settled")
        CANCELED = "canceled", _("Cancelled")
        PENDAUTH = "pend_auth", _("Pending Authorization")

    status = models.CharField(
        max_length=24,
        default=Status.DRAFT,
        choices=Status.choices,
        help_text="The status of the cashflow"
    )

    periodicity = RecurrenceField(null=True, blank=True)
    periodicity_start_date = models.DateField(null=True, blank=True)
    periodicity_end_date = models.DateField(null=True, blank=True)

    # ========================================================================================
    # Additional information
    # ========================================================================================
    name = models.CharField(max_length=255, null=True, blank=True, help_text="A name for the cashflow")
    description = models.TextField(null=True, blank=True, help_text="A description of the cashflow")

    installment = models.BooleanField(default=False)
    recurring = models.BooleanField(default=False)

    # =================================================
    # Approval Fields
    # =================================================
    approval_method = models.CharField(max_length=50, choices=ApprovalMethod.choices, null=True)
    approval_trigger = models.CharField(max_length=50, choices=ApprovalTriggerMethod.choices, null=True)
    is_dual_approval = models.BooleanField(default=False)
    approver_1 = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='cashflow_approver_1')
    approver_2 = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='cashflow_approver_2')
    approval_date_1 = models.DateTimeField(null=True)
    approval_date_2 = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.name} ({self.pk})"

    def generate_cashflows(self, installments: Optional[List[dict]] = None) -> List[SingleCashFlow]:
        cashflows = []

        # Create recurrence cashflows
        if self.periodicity:
            recurrence_provider = RecurrenceProvider(periodicity=self.periodicity,
                                             periodicity_start_date=self.periodicity_start_date,
                                             periodicity_end_date=self.periodicity_end_date)
            occurrences = recurrence_provider.get_occurrence_dates(sell_currency=self.sell_currency,
                                                                   buy_currency=self.buy_currency)

            for occurrence in occurrences:
                cashflow = SingleCashFlow(
                    amount=self.amount,
                    cntr_amount=self.cntr_amount,
                    buy_currency=self.buy_currency,
                    company=self.company,
                    description=self.description,
                    name=self.name,
                    pay_date=self.format_date(occurrence.date()) if isinstance(occurrence, datetime)\
                          else self.format_date(occurrence),
                    sell_currency=self.sell_currency,
                    status=SingleCashFlow.Status.DRAFT,
                    generator=self,
                    lock_side=self.lock_side
                )
                cashflow.save()
                cashflows.append(cashflow)
        # Create installments cashflows
        elif self.installment and installments:
            for installment in installments:
                sell_currency = Currency.get_currency(currency=installment['sell_currency'])
                buy_currency = Currency.get_currency(currency=installment['buy_currency'])
                lock_side = Currency.get_currency(currency=installment['lock_side'])

                cashflow = SingleCashFlow(
                    amount=installment['amount'],
                    cntr_amount=installment['cntr_amount'],
                    buy_currency=buy_currency,
                    company=self.company,
                    description=self.description,
                    generator=self,
                    lock_side=lock_side,
                    name=self.name,
                    pay_date=self.format_date(date=installment['date']),
                    sell_currency=sell_currency,
                    status=SingleCashFlow.Status.DRAFT
                )
                cashflow.save()
                cashflows.append(cashflow)
        elif not self.installment and not self.recurring:
            # Create one-time payment cashflow
            cashflow = SingleCashFlow(
                amount=self.amount,
                cntr_amount=self.cntr_amount,
                buy_currency=self.buy_currency,
                company=self.company,
                description=self.description,
                name=self.name,
                pay_date=self.format_date(date=self.value_date),
                sell_currency=self.sell_currency,
                status=SingleCashFlow.Status.DRAFT,
                generator=self,
                lock_side=self.lock_side
            )
            cashflow.save()
            cashflows.append(cashflow)

        return cashflows

    def update_cashflows(self, installments: Optional[List[dict]] = None,
                         recreate_recurrence: bool = False) -> List[SingleCashFlow]:
        cashflows = []

        # Update recurrence cashflows
        if self.periodicity and recreate_recurrence:
            recurrence_provider = RecurrenceProvider(periodicity=self.periodicity,
                                             periodicity_start_date=self.periodicity_start_date,
                                             periodicity_end_date=self.periodicity_end_date)
            occurrences = recurrence_provider.get_occurrence_dates(sell_currency=self.sell_currency,
                                                                   buy_currency=self.buy_currency)

            for occurrence in occurrences:
                cashflow = SingleCashFlow(
                    amount=self.amount,
                    cntr_amount=self.cntr_amount,
                    buy_currency=self.buy_currency,
                    company=self.company,
                    description=self.description,
                    name=self.name,
                    pay_date=self.format_date(occurrence.date()) if isinstance(occurrence, datetime)\
                          else self.format_date(occurrence),
                    sell_currency=self.sell_currency,
                    status=SingleCashFlow.Status.DRAFT,
                    generator=self,
                    lock_side=self.lock_side
                )
                cashflow.save()
                cashflows.append(cashflow)
            return cashflows
        elif self.installment and installments:
            for installment in installments:
                sell_currency = Currency.get_currency(currency=installment['sell_currency'])
                buy_currency = Currency.get_currency(currency=installment['buy_currency'])
                lock_side = Currency.get_currency(currency=installment['lock_side'])

                if 'cashflow_id' in installment.keys():
                    installment_cashflow = SingleCashFlow.objects.get(cashflow_id=uuid.UUID(installment['cashflow_id']))
                    installment_cashflow.amount = installment['amount']
                    installment_cashflow.cntr_amount = installment['cntr_amount']
                    installment_cashflow.buy_currency = buy_currency
                    installment_cashflow.pay_date = self.format_date(date=installment['date'])
                    installment_cashflow.sell_currency = sell_currency
                    installment_cashflow.save()
                    cashflows.append(installment_cashflow)
                    continue

                cashflow = SingleCashFlow(
                    amount=installment['amount'],
                    cntr_amount=installment['cntr_amount'],
                    buy_currency=buy_currency,
                    company=self.company,
                    description=self.description,
                    generator=self,
                    lock_side=lock_side,
                    name=self.name,
                    pay_date=self.format_date(date=installment['date']),
                    sell_currency=sell_currency,
                    status=SingleCashFlow.Status.DRAFT
                )
                cashflow.save()
                cashflows.append(cashflow)
        elif not self.installment and not self.recurring and recreate_recurrence:
            single_cashflow = SingleCashFlow(
                amount=self.amount,
                cntr_amount=self.cntr_amount,
                buy_currency=self.buy_currency,
                company=self.company,
                description=self.description,
                name=self.name,
                pay_date=self.format_date(date=self.value_date),
                sell_currency=self.sell_currency,
                status=SingleCashFlow.Status.DRAFT,
                generator=self,
                lock_side=self.lock_side
            )
            single_cashflow.save()
            cashflows.append(single_cashflow)
        elif not self.installment and not self.recurring:
            # Edit one-time payment cashflow
            single_cashflow = SingleCashFlow.objects.get(generator=self)
            single_cashflow.amount = self.amount
            single_cashflow.cntr_amount = self.cntr_amount
            single_cashflow.buy_currency = self.buy_currency
            single_cashflow.company = self.company
            single_cashflow.description = self.description
            single_cashflow.name = self.name
            single_cashflow.pay_date = self.format_date(date=self.value_date)
            single_cashflow.sell_currency = self.sell_currency
            single_cashflow.status = SingleCashFlow.Status.DRAFT
            single_cashflow.generator = self
            single_cashflow.lock_side = self.lock_side
            single_cashflow.save()
            cashflows.append(single_cashflow)

        return cashflows

    def format_date(self, date: Union[pydate, datetime]) -> datetime:
        if isinstance(date, pydate):
            return datetime(
                year=date.year,
                month=date.month,
                day=date.day,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
                tzinfo=pytz.utc
            )
        return date
