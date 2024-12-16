from rest_framework import serializers
from main.apps.currency.api.serializers.models.currency import FxPairSerializer
from main.apps.marketdata.models.fx.rate import (
    FxSpot,
    FxSpotIntra,
    FxSpotRange,
)
from main.apps.marketdata.models.fx.estimator import FxSpotVol


class AbstractFxSpotSerializer(serializers.ModelSerializer):
    pair = FxPairSerializer()

    class Meta:
        abstract = True
        fields = ("date", "pair", "rate", "rate_bid", "rate_ask")


class FxSpotSerializer(AbstractFxSpotSerializer):
    class Meta:
        model = FxSpot
        fields = AbstractFxSpotSerializer.Meta.fields


class FxSpotVolSerializer(serializers.ModelSerializer):
    class Meta:
        model = FxSpotVol
        fields = '__all__'


class FxSpotIntraSerializer(AbstractFxSpotSerializer):
    data_cut = None

    class Meta:
        model = FxSpotIntra
        fields = AbstractFxSpotSerializer.Meta.fields


class AbstractFxSpotRangeSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        fields = ("date", "pair",
                  "open_bid", "open_ask", "open",
                  "low_bid", "low_ask", "low",
                  "high_bid", "high_ask", "high")


class FxSpotRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FxSpotRange
        fields = AbstractFxSpotRangeSerializer.Meta.fields


class AverageFxSpotPriceSerializer(AbstractFxSpotSerializer):
    average_rate = serializers.FloatField()
    average_rate_bid = serializers.FloatField()
    average_rate_ask = serializers.FloatField()

    class Meta:
        model = FxSpotIntra
        fields = ("pair", 'average_rate', 'average_rate_bid', 'average_rate_ask')


class AverageFxSpotPriceRequestSerializer(serializers.Serializer):
    pair_id = serializers.IntegerField(required=True)
