from typing import List
from django.db import models
from django.utils.translation import gettext_lazy as _
from main.apps.currency.models import Currency


class CurrencyDefinition(models.Model):
    currency = models.OneToOneField(Currency, on_delete=models.CASCADE)
    p10 = models.BooleanField(default=False)
    wallet = models.BooleanField(default=False)
    wallet_api = models.BooleanField(default=False)
    ndf = models.BooleanField(default=False)
    fwd_delivery_buying = models.BooleanField(default=False)
    fwd_delivery_selling = models.BooleanField(default=False)
    outgoing_payments = models.BooleanField(default=False)
    incoming_payments = models.BooleanField(default=False)

    @staticmethod
    def get_all_wallet_api_currencies() -> List[Currency]:
        currencies = []
        for definition in CurrencyDefinition.objects.filter(wallet_api=True):
            currencies.append(definition.currency)
        return currencies

    @staticmethod
    def get_p10_currencies() -> List[Currency]:
        currencies = []
        for definition in  CurrencyDefinition.objects.filter(p10=True):
            currencies.append(definition.currency)
        return currencies

    @staticmethod
    def get_other_currencies() -> List[Currency]:
        currencies = []
        for definition in CurrencyDefinition.objects.filter(p10=False):
            currencies.append(definition.currency)
        return currencies

    def get_all_ndf_api_currencies(status: bool = False) -> List[Currency]:
        currencies = []
        for definition in CurrencyDefinition.objects.filter(ndf=status):
            currencies.append(definition.currency)
        return currencies

    @staticmethod
    def get_forward_currencies() -> List[Currency]:
        currencies = []
        for definition in CurrencyDefinition.objects.filter(fwd_delivery_buying=True, fwd_delivery_selling=True):
            currencies.append(definition.currency)
        return currencies

    @staticmethod
    def get_forward_buying_currencies() -> List[Currency]:
        currencies = []
        for definition in CurrencyDefinition.objects.filter(fwd_delivery_buying=True):
            currencies.append(definition.currency)
        return currencies

    @staticmethod
    def get_forward_selling_currencies() -> List[Currency]:
        currencies = []
        for definition in CurrencyDefinition.objects.filter(fwd_delivery_selling=True):
            currencies.append(definition.currency)
        return currencies
