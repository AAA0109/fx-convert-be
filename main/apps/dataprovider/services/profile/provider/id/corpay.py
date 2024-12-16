from typing import Optional, Sequence
from django.db.models import Q

from main.apps.corpay.models import CurrencyDefinition, CorpaySettings
from main.apps.currency.models import FxPair
from main.apps.currency.models.currency import Currency
from main.apps.dataprovider.services.profile.provider.base import BaseProvider


class CorpayBaseProvider(BaseProvider):
    base_currency: Currency
 
    def __init__(self, base_currency:Optional[str] = None) -> None:
        super().__init__()
        self.base_currency = Currency.get_currency(currency=base_currency) if base_currency else None

    def build_queries(self, base_definitions: Sequence[CurrencyDefinition], quote_definitions: Sequence[CurrencyDefinition]):
        pair_cache = []
        queries = Q()
        for base_definition in base_definitions:
            for quote_definition in quote_definitions:
                if quote_definition.currency.pk == base_definition.currency.pk:
                    continue
                if self.base_currency and base_definition.currency != self.base_currency:
                    continue
                cache_key = f"{quote_definition.currency.pk}-{base_definition.currency.pk}"
                inverse_cache_key = f"{base_definition.currency.pk}-{quote_definition.currency.pk}"
                if cache_key in pair_cache or inverse_cache_key in pair_cache:
                    continue
                pair_cache.append(cache_key)
                pair_cache.append(inverse_cache_key)
                queries |= Q(base_currency=base_definition.currency, quote_currency=quote_definition.currency)
        return queries


class CorpayFxPairSpotProvider(CorpayBaseProvider):
    def get_ids(self):
        definitions = CurrencyDefinition.objects.all()
        queries = self.build_queries(definitions, definitions)
        qs = FxPair.objects.filter(queries)
        return self.get_ids_from_queryset(qs)


class CorpayFxForwardProvider(CorpayBaseProvider):
    def get_ids(self):
        fwd_sell_currencies = CurrencyDefinition.objects.filter(fwd_delivery_selling=True)
        queries = self.build_queries(fwd_sell_currencies, fwd_sell_currencies)
        qs = FxPair.objects.filter(queries)
        return self.get_ids_from_queryset(qs)


class CorpayCompanyProvider(BaseProvider):
    def get_ids(self):
        qs = CorpaySettings.objects.all().values_list('company_id', flat=True)
        return list(qs)
