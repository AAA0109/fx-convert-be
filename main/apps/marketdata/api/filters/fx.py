import django_filters


class FxFilterSet(django_filters.FilterSet):
    base_currency = django_filters.CharFilter(field_name='pair__base_currency__mnemonic', lookup_expr='icontains')
    quote_currency = django_filters.CharFilter(field_name='pair__quote_currency__mnemonic', lookup_expr='icontains')


def get_spot_filter_for_model(model_instance):
    class GenericFxSpotFilterSet(FxFilterSet):
        class Meta:
            model = model_instance
            fields = ['base_currency', 'quote_currency']

    return GenericFxSpotFilterSet


def get_forward_filter_for_model(model_instance):
    class GenericFxForwardFilterSet(FxFilterSet):
        TENOR_CHOICES = (
            ('1W', '1 Weeks'),
            ('3W', '3 Weeks'),
            ('1M', '1 Month'),
            ('1Y', '1 Year')
        )
        tenor = django_filters.ChoiceFilter(choices=TENOR_CHOICES)

        class Meta:
            model = model_instance
            fields = ['base_currency', 'quote_currency', 'tenor']

    return GenericFxForwardFilterSet
