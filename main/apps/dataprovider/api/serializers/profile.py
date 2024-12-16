from rest_framework import serializers


class ProfileParallelOptionRequestSerializer(serializers.Serializer):
    profile_id = serializers.IntegerField()


class ProfileParallelOptionResponseSerializer(serializers.Serializer):
    field = serializers.CharField()
    ids = serializers.ListSerializer(child=serializers.IntegerField())
