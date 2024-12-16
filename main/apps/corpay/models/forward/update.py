from django.db import models
from django.utils.translation import gettext as _
from django_extensions.db.models import TimeStampedModel

from main.apps.account import models as account
from main.apps.account.models import CashFlow
from main.apps.currency import models as currency
from main.apps.corpay.models.currency import CurrencyDefinition


class UpdateRequest(TimeStampedModel):
    class RequestType(models.TextChoices):
        CASHFLOW = 'cashflow_details', _('Cashflow Details')
        RISK_DETAILS = 'risk_details', _('Risk Details')
        DRAWDOWN = 'drawdown', _('drawdown')
        NSF = 'nsf', _('Non sellable forward')
        NDF = 'ndf', _('Non deliverable forward')

    class RequestStatus(models.TextChoices):
        NEW = 'new', _('New')
        REVIEWED = 'reviewed', _('Reviewed')
        PROCESSING = 'processing', _('Processing')
        PROCESSED = 'processed', _('Processed')
        CLOSED = 'closed', _('Closed')

    type = models.CharField(choices=RequestType.choices, null=False)
    request_details = models.TextField()
    status = models.CharField(choices=RequestStatus.choices, null=False, default=RequestStatus.NEW)
    user = models.ForeignKey('account.User', related_name='request', on_delete=models.SET_NULL, null=True)
    company = models.ForeignKey('account.Company', related_name='request', on_delete=models.SET_NULL, null=True)


class ManualForwardRequest(TimeStampedModel):
    request = models.OneToOneField(UpdateRequest, on_delete=models.CASCADE, related_name='ndf_request', null=False)
    pair = models.ForeignKey('currency.FxPair', on_delete=models.CASCADE, null=False)
    amount = models.FloatField()
    delivery_date = models.DateField()
    cashflow = models.ForeignKey(CashFlow, on_delete=models.CASCADE, null=True, blank=True)

    __currencies: dict = {}

    @staticmethod
    def currencies():
        if not ManualForwardRequest.__currencies:
            for item in CurrencyDefinition.objects.all():
                ManualForwardRequest.__currencies.update({item.currency_id: {
                    'ndf': item.ndf,
                    'buying': item.fwd_delivery_buying,
                    'selling': item.fwd_delivery_selling,
                }})
        return ManualForwardRequest.__currencies

    @staticmethod
    def is_ndf(cashflow: account.CashFlow):
        currency_info = ManualForwardRequest.currencies()[cashflow.currency.pk]
        return currency_info['ndf']

    @staticmethod
    def is_nsf(cashflow: account.CashFlow):
        currency_info = ManualForwardRequest.currencies()[cashflow.currency.pk]

        if cashflow.amount < 0 and not currency_info['buying']:
            return True

        if cashflow.amount > 0 and not currency_info['selling']:
            return True

        return False

    @staticmethod
    def is_manual(cashflow: account.CashFlow):
        return (ManualForwardRequest.is_ndf(cashflow) or
                ManualForwardRequest.is_nsf(cashflow))

    @staticmethod
    def create(pair: currency.FxPair, amount, delivery_date,
               type: UpdateRequest.RequestType = UpdateRequest.RequestType.NDF,
               user: 'account.User' = None, company: 'account.Company' = None, cashflow= None) -> 'ManualForwardRequest':
        request = UpdateRequest.objects.create(
            type=type,
            request_details=f'new: {type.name}',
            user=user,
            company=company
        )
        return ManualForwardRequest.objects.create(
            request=request,
            pair=pair,
            amount=amount,
            delivery_date=delivery_date,
            cashflow=cashflow,
        )

    @staticmethod
    def create_from_cashflow(pair: currency.FxPair, cashflow: account.CashFlow) -> 'ManualForwardRequest':
        if ManualForwardRequest.is_ndf(cashflow):
            request_type = UpdateRequest.RequestType.NDF
        elif ManualForwardRequest.is_nsf(cashflow):
            request_type = UpdateRequest.RequestType.NSF
        else:
            raise Exception('Should be manual')

        cashflow.save()
        return ManualForwardRequest.create(pair=pair, amount=cashflow.amount,
                                           delivery_date=cashflow.date, type=request_type,
                                           company=cashflow.account.company, cashflow=cashflow)
