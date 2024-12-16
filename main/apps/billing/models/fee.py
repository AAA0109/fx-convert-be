from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as __

from main.apps.account.models.company import Company
from main.apps.account.models.cashflow import CashFlow
from main.apps.billing.models.payment import Payment

from hdlib.DateTime.Date import Date

from typing import Sequence, Optional, Tuple, Union, Iterable

import logging

logger = logging.getLogger(__name__)


class Fee(models.Model):
    """
    Pangea fees model. Each fee is invoiced to a customer, for a particular reason (e.g. a daily AUM maintenance fee,
    a new cashflow fee)
    """

    class Meta:
        verbose_name_plural = "fees"

    # Amount (always in USD)
    amount = models.FloatField(null=False)

    # When was this fee incurred, ie what time in history do we trace the fee back to
    incurred = models.DateTimeField(auto_now_add=False, blank=False, null=False)

    # When this fee was recorded in our system
    recorded = models.DateTimeField(auto_now_add=True, blank=False)

    # When this fee is due
    due = models.DateTimeField(auto_now_add=False, blank=False)

    # When this fee was settled (e.g. as paid, or wavied, etc)
    settled = models.DateTimeField(auto_now_add=False, blank=True, null=True)

    # Company to which the fee is tied
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='companies', null=False)

    # Cashflow to which the fee is tied (optional), only cashflow specific fees
    cashflow = models.ForeignKey(CashFlow, on_delete=models.CASCADE, related_name='cashflows', null=True)

    # Payment id when a fee is settled as paid, to link it back to the payment used to settle
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='fee_payments', null=True)

    class FeeType(models.TextChoices):
        NEW_CASHFLOW = "new_cashflow", __("NEW_CASHFLOW")
        MAINTENANCE = "maintenance", __("MAINTENANCE")
        SETTLEMENT = "settlement", __("SETTLEMENT")

    # Type of fee
    fee_type = models.CharField(max_length=24, null=False, choices=FeeType.choices)

    class Status(models.TextChoices):
        DUE = "due", __("DUE")  # A fee that has not been paid, and is due at some time in the future
        PAID = "paid", __("PAID")  # A paid fee
        WAIVED = "waived", __("WAIVED")  # A fee that was invoiced was later waived

    # Payment status of fee
    status = models.CharField(max_length=24, default=Status.DUE, choices=Status.choices)

    def get_payment_type(self) -> Optional[Payment.PaymentType]:
        return self.map_fee_type_to_payment_type(fee_type=self.fee_type)

    @staticmethod
    def map_fee_type_to_payment_type(fee_type: Union[FeeType, str]) -> Optional[Payment.PaymentType]:
        map_ = {Fee.FeeType.NEW_CASHFLOW: Payment.PaymentType.ONE_TIME,
                Fee.FeeType.SETTLEMENT: Payment.PaymentType.ONE_TIME,
                Fee.FeeType.MAINTENANCE: Payment.PaymentType.MONTHLY}
        return map_.get(fee_type, None)

    def is_overdue(self, ref_date: Optional[Date] = None) -> bool:
        """
        Check if a fee is overdue for payment as of some reference date
        :param ref_date: Date of reference (defaults to now)
        :return: True if the fee is due and its due date is strictly before the supplied reference date
        """
        if not ref_date:
            ref_date = Date.now()
        due_date = Date.to_date(self.due)
        return self.status == Fee.Status.DUE and ref_date > due_date

    def is_settled(self) -> bool:
        return self.status != Fee.Status.DUE

    def is_waived(self) -> bool:
        return self.status == Fee.Status.WAIVED

    def settle(self,
               status: Status = Status.PAID,
               payment: Optional[Payment] = None,
               datetime: Optional[Date] = None):
        """
        Settle a fee as being paid (or waived), or otherwise no longer payable
        :param status: Status, the status to change this fee to upon this settlement
        :param datetime: Date, the time of settlement
        """
        if not datetime:
            datetime = Date.now()

        self.status = status
        self.settled = datetime
        self.payment = payment
        self.save()

    def payment_status(self) -> Payment.PaymentStatus:
        return Payment.PaymentStatus(self.payment.payment_status)

    class NotFound(Exception):
        def __init__(self):
            super(Fee.NotFound, self).__init__()

auditlog.register(Fee)
