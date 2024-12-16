from rest_framework import serializers


class StripeSetupIntentSerializer(serializers.Serializer):
    client_secret = serializers.CharField()
