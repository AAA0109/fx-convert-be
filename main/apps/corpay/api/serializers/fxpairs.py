from rest_framework import serializers

from main.apps.corpay.models import SupportedFxPairs


class SupportedFxPairsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportedFxPairs
        fields = '__all__'
