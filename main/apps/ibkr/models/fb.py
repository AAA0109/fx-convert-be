from auditlog.registry import auditlog
from django.db import models
from django.utils.translation import gettext_lazy as __
from django_extensions.db.models import TimeStampedModel

from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import Currency


class FundingRequest(TimeStampedModel):
    method = models.CharField(max_length=255, null=False)
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name='funding_requests')
    request_submitted = models.BooleanField(default=False)
    response_data = models.JSONField(null=True)


auditlog.register(FundingRequest)


class FundingRequestStatus(TimeStampedModel):
    class RequestStatus(models.TextChoices):
        ERROR = 'error', __('Error')
        UNKNOWN = 'unknown', __('Unknown')
        REQUEST_REJECTED = 'request_rejected', __('Request Rejected')
        REQUEST_ACCEPTED_FOR_PROCESSING = 'request_accepted_for_processing', __('Request Accepted for Processing')

    funding_request = models.OneToOneField(FundingRequest, on_delete=models.CASCADE,
                                           related_name='status')
    timestamp = models.DateTimeField(null=True, blank=True)
    request_status = models.CharField(max_length=60, null=True, blank=True, choices=RequestStatus.choices)
    details = models.TextField(null=True, blank=True)
    error_code = models.CharField(max_length=255, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)


auditlog.register(FundingRequestStatus)


class FundingRequestProcessingStat(TimeStampedModel):
    funding_request = models.OneToOneField(FundingRequest, on_delete=models.CASCADE,
                                           related_name='processing_stat')
    instruction_set_id = models.IntegerField(null=True, blank=True)
    trans_read = models.IntegerField(null=True, blank=True)
    trans_understood = models.IntegerField(null=True, blank=True)
    trans_provided = models.IntegerField(null=True, blank=True)
    trans_rejected = models.IntegerField(null=True, blank=True)


auditlog.register(FundingRequestProcessingStat)


class AbstractFundingRequestResult(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', __('Pending')
        PROCESSED = 'processed', __('Processed')
        REJECTED = 'rejected', __('Rejected')

    funding_request = models.OneToOneField(FundingRequest, on_delete=models.CASCADE)
    ib_instr_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=11, null=False, default=Status.PENDING,
                              choices=Status.choices)
    code = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True


class FundingRequestResult(AbstractFundingRequestResult):
    funding_request = models.OneToOneField(FundingRequest, on_delete=models.CASCADE, related_name="result")


auditlog.register(FundingRequestResult)


class AbstractDepositWithdrawResult(AbstractFundingRequestResult):
    amount = models.FloatField(null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    method = models.CharField(null=True, blank=True, max_length=10)
    saved_instruction_name = models.CharField(null=True, blank=True, max_length=60)

    class Meta:
        abstract = True


class DepositResult(AbstractDepositWithdrawResult):
    funding_request = models.OneToOneField(FundingRequest, on_delete=models.CASCADE, related_name="deposit_result")


auditlog.register(DepositResult)


class WithdrawResult(AbstractDepositWithdrawResult):
    funding_request = models.OneToOneField(FundingRequest, on_delete=models.CASCADE, related_name="withdraw_result")


auditlog.register(WithdrawResult)
