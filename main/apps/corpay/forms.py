import uuid

from django import forms
from django.forms import SelectDateWidget
from hdlib.DateTime.Date import Date

from main.apps.account.models import Company, Account, CashFlow
from main.apps.corpay.models import UpdateRequest, Locksides
from main.apps.corpay.services.corpay import CorPayService
from main.apps.currency.models.fxpair import FxPair
from main.apps.hedge.models import FxForwardPosition


class FxForwardPositionForm(forms.ModelForm):
    delivery_time = forms.DateField(label='Delivery date', required=True, widget=SelectDateWidget)

    class Meta:
        model = FxForwardPosition
        fields = ['forward_price', 'amount', 'delivery_time']

    def save(self, commit=True):
        super(FxForwardPositionForm, self).save()
        cashflow = self.instance.cashflow
        cashflow.date = self.instance.delivery_time
        cashflow.save()

        if self.instance.unwind_time and cashflow.date > self.instance.unwind_time:
            self.instance.unwind_time = None
            self.instance.unwind_price = None
            self.instance.save()
        return self.instance


class ManualForm(forms.Form):
    """
    Handle Manual Request from outside platform
    Create: CF, Account, and FxForwardPosition
    """
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        to_field_name='pk',
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cashflow_name = forms.CharField()
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        to_field_name='pk',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select a existing Account'
    )
    amount = forms.FloatField(label='amount', min_value=0)
    delivery_date = forms.DateField(label='Delivery date', required=True, widget=SelectDateWidget)

    pair = forms.ModelChoiceField(
        queryset=FxPair.objects.all(),
        to_field_name='pk',
        required=True,
    )

    def __init__(self, instance: UpdateRequest, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        company = self.initial.get('company')

        # Select choices on Account
        if company:
            account_qs = Account.objects.filter(company=company)
        else:
            account_qs = Account.objects.all()
        account_qs = account_qs.filter(is_active=True)
        choices = [(None, '----------')] + [(obj.pk, str(obj)) for obj in account_qs.order_by('pk')]
        self.fields['account'].choices = choices

    def clean(self):
        # Validation company X new Account.company
        company = self.cleaned_data['company']
        account = self.cleaned_data.get('account')
        if company and account and company.pk != account.company_id:
            self.add_error('account', "Company and Company's Account do not match.")

    def save(self):
        if self.instance.ndf_request and self.instance.ndf_request.cashflow:
            raise NotImplemented()

        company = self.cleaned_data['company']  # type: Company
        pair = self.cleaned_data['pair']  # type: fxpair
        corpay_service = CorPayService()
        corpay_service.company = company
        corpay_service.init_company(company)

        account = Account.create_account(
            name=uuid.uuid4().hex,
            company=self.cleaned_data['company'],
            account_type=Account.AccountType.LIVE,
            is_active=True,
            is_hidden=True,
        )
        cashflow = CashFlow.create_cashflow(account=account,
                                            name=self.cleaned_data['cashflow_name'],
                                            date=self.cleaned_data['delivery_date'],
                                            currency=company.currency,
                                            amount=self.cleaned_data['amount'],
                                            status=CashFlow.CashflowStatus.ACTIVE,
                                            save=True
                                            )
        forward_quote = corpay_service.request_quote(pair, cashflow.amount, Date.from_datetime_date(cashflow.date),
                                                     cashflow.id, Locksides.Payment, True)
        FxForwardPosition.objects.create(
            cashflow=cashflow,
            fxpair=forward_quote.fx_pair,
            amount=forward_quote.amount,
            delivery_time=cashflow.date,
            enter_time=forward_quote.forward_guideline.bookdate,
            forward_price=forward_quote.forward_price()
        )

        self.instance.ndf_request.cashflow = cashflow
        self.instance.ndf_request.save()
