from rest_framework import serializers

from main.apps.marketdata.models import IndexAsset


class IndexAssetSerializer(serializers.ModelSerializer):

    class Meta:
        model = IndexAsset
        fields = ("name", "symbol")
