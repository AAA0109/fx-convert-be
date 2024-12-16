from rest_framework import serializers


class ResourceAlreadyExists(serializers.Serializer):
    field = serializers.CharField(required=False)
    message = serializers.CharField(required=False)
