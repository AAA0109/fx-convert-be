from rest_framework import serializers

from main.apps.corpay.api.serializers.base import ValueSetSerializer


class ProxyRequestSerializer(serializers.Serializer):
    uri = serializers.URLField()
    METHODS = (
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PATCH', 'PATCH'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE')
    )
    method = serializers.ChoiceField(choices=METHODS)


class ProxyRegionSerializer(serializers.Serializer):
    id = serializers.CharField()
    country = serializers.CharField()
    country_name = serializers.CharField(source="countryName")
    name = serializers.CharField()


class ProxyRegionResponseSerializer(serializers.Serializer):
    regions = ProxyRegionSerializer(many=True)
    is_complete_list = serializers.BooleanField(source="isCompleteList")
    value_set = ValueSetSerializer(many=True, source='valueSet')


class ProxyCountrySerializer(serializers.Serializer):
    name = serializers.CharField(source="countryName")
    country = serializers.CharField()
    default_currency = serializers.CharField(source="defaultCurrency")


class ProxyCountryResponseSerializer(serializers.Serializer):
    countries = ProxyCountrySerializer(many=True)
    value_set = ValueSetSerializer(many=True, source='valueSet')


class ProxyCurrencySerializer(serializers.Serializer):
    curr = serializers.CharField()
    desc = serializers.CharField()


class ProxyCurrencyResponseSerializer(serializers.Serializer):
    common = serializers.ListSerializer(child=serializers.CharField())
    all = ProxyCurrencySerializer(many=True)
    value_set = ValueSetSerializer(many=True, source='valueSet')
