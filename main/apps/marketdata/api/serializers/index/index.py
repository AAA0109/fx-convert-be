from rest_framework import serializers

from main.apps.marketdata.api.serializers.index.index_asset import IndexAssetSerializer
from main.apps.marketdata.models import Index


class AbstractIndexSerializer(serializers.ModelSerializer):
    index_asset = IndexAssetSerializer()

    class Meta:
        abstract = True
        fields = ("date", "index_asset", "rate_index",
                  "rate_bid_index", "rate_ask_index")


class IndexSerializer(AbstractIndexSerializer):

    class Meta:
        model = Index
        fields = AbstractIndexSerializer.Meta.fields
