from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as __
from django_extensions.db.models import TimeStampedModel


# Create your models here.
class Payment(TimeStampedModel):
    # Amount Paid (actual payment amount, in dollars)
    amount = models.FloatField(null=False)
    # Payment method
    method = models.CharField(max_length=255, null=True, blank=True)

    class PaymentType(models.TextChoices):
        ONE_TIME = "one_time", __("One Time")
        MONTHLY = "monthly", __("Monthly")

    class PaymentStatus(models.TextChoices):
        INITIATED = "initiated", __("Initiated")
        SUCCESS = "success", __("Success")
        ERROR = "error", __("Error")

    payment_type = models.CharField(max_length=24, null=False, choices=PaymentType.choices)
    payment_status = models.CharField(max_length=24, null=False, choices=PaymentStatus.choices,
                                      default=PaymentStatus.INITIATED)
    class MissingPaymentMethod(Exception):
        def __init__(self, company):
            super().__init__(f"Missing payment method for company: {company}")

    class PaymentChargeFailure(Exception):
        def __init__(self, company):
            super().__init__(f"Failed to charge company: {company}")


auditlog.register(Payment)


class Transaction(TimeStampedModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    # Transaction ID from payment provider
    txn_id = models.CharField(max_length=255, null=True, blank=True)

    class TransactionType(models.TextChoices):
        ORDER = "order", __("Order")
        AUTH = "auth", __("Authorization"),
        VOID = "void", __("Void"),
        CAPTURE = "capture", __("Capture")


auditlog.register(Transaction)
