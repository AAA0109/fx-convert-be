from rest_framework import serializers


class ActionStatusSerializer(serializers.Serializer):
    message = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    code = serializers.IntegerField(required=False)
    data = serializers.JSONField(required=False)
