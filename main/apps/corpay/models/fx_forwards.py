from functools import cached_property
from typing import List

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from hdlib.DateTime.Date import Date

from main.apps.account.models import CashFlow, Company
from main.apps.corpay.models import CorpaySettings
from main.apps.corpay.models.choices import DestinationAccountType, Locksides, RateOperation
from main.apps.currency.models import Currency, FxPair


class SupportedFxPairs(TimeStampedModel):
    class FxPairType(models.TextChoices):
        P20 = ('p20', 'P20')
        WALLET = ('wallet', 'Wallet')
        OTHER = ('other', 'Other')

    """
    This class stores the Corpay supported fx pairs
    """
    fx_pair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)
    fx_pair_type = models.CharField(choices=FxPairType.choices, max_length=60)


class ForwardGuidelines(TimeStampedModel):
    credentials = models.ForeignKey(CorpaySettings, on_delete=models.CASCADE, null=False)
    base_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False)
    bookdate = models.DateTimeField(null=False)

    forward_maturity_days = models.IntegerField(null=False)
    client_limit_amount = models.FloatField(null=False)
    client_limit_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False,
                                              related_name="quote_client_limit_currency")
    allow_book_deals = models.BooleanField(null=False)
    forward_max_open_contract_interval = models.IntegerField(null=False)
    margin_call_percent = models.FloatField(null=False)
    max_days = models.IntegerField(null=False)
    hedging_agreement = models.BooleanField(null=False)
    allow_book = models.BooleanField(null=False)

    @property
    def delivery_time(self) -> Date:
        return Date.from_datetime_date(self.bookdate) + self.forward_maturity_days


class ForwardQuote(TimeStampedModel):
    forward_guideline = models.ForeignKey(ForwardGuidelines, on_delete=models.CASCADE, null=False,
                                          related_name="quote_forward_guideline")
    quote_id = models.CharField(null=False, max_length=32)
    rate_value = models.FloatField(null=False)
    rate_lockside = models.CharField(max_length=24, choices=Locksides.choices, null=False)
    rate_type = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False, related_name="quote_rate_type")
    rate_operation = models.CharField(max_length=24, choices=RateOperation.choices, null=False)
    payment_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False,
                                         related_name="quote_payment_currency")
    payment_amount = models.FloatField(null=False)
    settlement_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False,
                                            related_name="quote_settlement_currency")
    settlement_amount = models.FloatField(null=False)
    cashflow = models.ForeignKey(CashFlow, on_delete=models.PROTECT, null=True, blank=True, related_name="quote_cashflow")

    @cached_property
    def fx_pair(self) -> FxPair:
        return FxPair.get_pair_from_currency(self.payment_currency, self.settlement_currency)

    def forward_price(self) -> float:
        return self.settlement_amount / self.payment_amount

    @property
    def amount(self):
        return self.payment_amount


class SpotRate(TimeStampedModel):
    user = models.ForeignKey('account.User', null=True, on_delete=models.SET_NULL)
    company = models.ForeignKey(Company, null=True, on_delete=models.SET_NULL)
    quote_id = models.CharField(null=False, max_length=32, unique=True)
    rate_value = models.FloatField(null=False)
    rate_lockside = models.CharField(max_length=24, choices=Locksides.choices, null=False)
    fx_pair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=True)
    rate_operation = models.CharField(max_length=24, choices=RateOperation.choices, null=False)
    payment_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, related_name="+")
    payment_amount = models.FloatField(null=False)
    settlement_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=False, related_name="+")
    settlement_amount = models.FloatField(null=False)
    order_number = models.CharField(max_length=60, null=True, blank=True)
    fx_balances = models.ManyToManyField('corpay.FXBalance')


class Forward(TimeStampedModel):
    forward_quote = models.OneToOneField(ForwardQuote, on_delete=models.CASCADE, null=False)
    corpay_forward_id = models.IntegerField(null=False)
    order_number = models.CharField(null=False, max_length=11)
    token = models.CharField(null=False, max_length=32)
    maturity_date = models.DateTimeField(null=False)

    # this filed will be populated when we have drawn this.
    drawdown_date = models.DateTimeField(null=True)

    # The drawdown order number
    drawdown_order_number = models.IntegerField(null=True)

    # Where to pull funds from during settlement
    origin_account = models.CharField(null=True, max_length=60)

    # Where to send funds to during settlement
    destination_account = models.CharField(null=True, max_length=60)

    # Destination account type
    destination_account_type = models.CharField(choices=DestinationAccountType.choices, max_length=1, null=True)

    # Where to pull funds from in case of insufficient balance in origin_account
    funding_account = models.CharField(null=True, max_length=60)

    # Account ID used for cash settlement
    cash_settle_account = models.CharField(null=True, max_length=60)

    # Purpose of payment
    purpose_of_payment = models.CharField(null=True, max_length=60)

    # Flag for cash settltment
    is_cash_settle = models.BooleanField(default=False)

    @staticmethod
    def get_drawdown_forwards(date: Date, company: Company) -> List['Forward']:
        """
        Get the forwards that are maturing strictly before the given date  and are not yet drawn down
        :param date: the maturity date
        :return:
        """
        # todo(ghais) check the logic for which forwards shuold we drowdown
        return Forward.objects.filter(maturity_date__lt=date,
                                      drawdown_date__isnull=True,
                                      forward_quote__forward_guideline__credentials__company=company)
