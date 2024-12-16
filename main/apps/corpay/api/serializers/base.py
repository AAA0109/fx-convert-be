from rest_framework import serializers


class LinkSerializer(serializers.Serializer):
    rel = serializers.CharField()
    uri = serializers.URLField()
    method = serializers.CharField()


class PaginationSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    skip = serializers.IntegerField()
    take = serializers.IntegerField()


class SortingSerializer(serializers.Serializer):
    column = serializers.CharField()
    dir = serializers.CharField()


class ValueSetSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField()


class ListDataSerializer(serializers.Serializer):
    pagination = PaginationSerializer()
    links = LinkSerializer(many=True)
    sorting = SortingSerializer(many=True)


class FacetSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField(required=False)
    count = serializers.IntegerField()


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class KeyValueSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.CharField()
