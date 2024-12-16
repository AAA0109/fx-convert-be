from typing import Iterable

from auditlog.registry import auditlog
from django.db import models
from django_extensions.db.models import TimeStampedModel
from django.utils.translation import gettext_lazy as __

from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import Currency
from main.apps.ibkr.models import FundingRequest


class Deposit(TimeStampedModel):
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, null=False, blank=False)
    amount = models.FloatField(null=False, blank=False)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, blank=False)

    class DepositMethod(models.TextChoices):
        ACHUS = "achus", __("ACHUS")
        ACHCA = "achca", __("ACHCA")
        WIRE = "wire", __("WIRE")

    method = models.CharField(max_length=11, null=False, blank=False, choices=DepositMethod.choices)

    class DepositStatus(models.TextChoices):
        PENDING = "pending", __("Pending")
        ACCEPTED = "accepted", __("Accepted")
        REJECTED = "rejected", __("Rejected")

    status = models.CharField(max_length=11, null=False, default=DepositStatus.PENDING, choices=DepositStatus.choices)

    funding_request = models.ForeignKey(FundingRequest, null=True, blank=True, on_delete=models.CASCADE)

    @staticmethod
    def get_pending_deposits(broker_account: BrokerAccount) -> Iterable['Deposit']:
        return Deposit.objects.filter(broker_account=broker_account, status=Deposit.DepositStatus.PENDING)


auditlog.register(Deposit)
