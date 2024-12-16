from rest_framework import serializers

from main.apps.currency.models import FxPair
from main.apps.marketdata.models import CorpayFxSpot, CorpayFxForward


class CorPayFxSpotSerializer(serializers.ModelSerializer):
    pair = serializers.StringRelatedField()

    class Meta:
        model = CorpayFxSpot
        fields = '__all__'


class CorPayFxForwardSerializer(serializers.ModelSerializer):
    pair = serializers.StringRelatedField()

    class Meta:
        model = CorpayFxForward
        fields = '__all__'
