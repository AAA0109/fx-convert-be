from rest_framework import serializers
from main.apps.country.api.serializers.models.country import CountrySerializer
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.deliverytime import DeliveryTime
from main.apps.currency.models.fxpair import FxPair
from main.apps.currency.models.stabilityIndex import StabilityIndex


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = (
            "id",
            "symbol",
            "mnemonic",
            "name",
            "unit",
            "numeric_code",
            "country",
            "image_thumbnail",
            "image_banner"
        )


class FxPairSerializer(serializers.ModelSerializer):
    base_currency = CurrencySerializer()
    quote_currency = CurrencySerializer()

    class Meta:
        model = FxPair
        fields = (
            "id",
            "base_currency",
            "quote_currency"
        )


class StabilityIndexSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer()

    class Meta:
        model = StabilityIndex
        fields = (
            "id",
            "date",
            "parent_index",
            "type",
            "name",
            "description",
            "value",
            "average_value",
            "rank",
            "currency"
        )

class CurrencyDeliveryTimeRequestSerializer(serializers.Serializer):
    currency = serializers.CharField()


class CurrencyDeliverySerializer(serializers.ModelSerializer):
    currency = CurrencySerializer()
    country = CountrySerializer()

    class Meta:
        model = DeliveryTime
        fields = "__all__"
