from django.db import models
from django.db.models import Q, Subquery

from main.apps.currency.models import FxPair, CurrencyTypes, Currency


class SupportedFxPair(models.Model):
    fxpair = models.OneToOneField(FxPair, on_delete=models.CASCADE)

    class Meta:
        ordering = ["fxpair__base_currency", "fxpair__quote_currency"]

    @staticmethod
    def get_ibkr_supported_pairs(base_currency: CurrencyTypes = None, quote_currency: CurrencyTypes = None):
        or_queries = []
        supported_query = SupportedFxPair.objects.values_list('fxpair_id', flat=True)
        qs = FxPair.objects.filter(id__in=supported_query)
        if base_currency is not None:
            base_currency = Currency.get_currency(base_currency)
            or_queries.append(Q(base_currency_id=base_currency.pk))
        if quote_currency is not None:
            quote_currency = Currency.get_currency(quote_currency)
            or_queries.append(Q(quote_currency_id=quote_currency.pk))
        if base_currency is not None or quote_currency is not None:
            or_filter = or_queries.pop()
            for item in or_queries:
                or_filter |= item
            qs = qs.filter(Q(base_currency_id=base_currency.pk) | Q(quote_currency_id=quote_currency.pk))
        return qs
