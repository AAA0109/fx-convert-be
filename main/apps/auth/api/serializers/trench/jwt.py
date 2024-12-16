from rest_framework import serializers


class MFAFirstStepJWTRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class MFAFirstStepJWTMFAEnabledSuccessResponseSerializer(serializers.Serializer):
    ephemeral_token = serializers.CharField()
    method = serializers.CharField()


class MFAJWTAccessRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class MFASecondStepJWTRequestSerializer(serializers.Serializer):
    ephemeral_token = serializers.CharField()
    code = serializers.CharField()
