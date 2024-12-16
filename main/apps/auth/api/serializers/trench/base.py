from rest_framework import serializers


class MFAConfigViewSuccessResponseSerializer(serializers.Serializer):
    methods = serializers.ListSerializer(child=serializers.CharField())
    confirm_disable_with_code = serializers.BooleanField()
    confirm_regeneration_with_code = serializers.BooleanField()
    allow_backup_codes_regeneration = serializers.BooleanField()


class MFAActiveUserMethodSerializer(serializers.Serializer):
    name = serializers.CharField()
    is_primary = serializers.BooleanField()


class MFAMethodDetailsResponseSerializer(serializers.Serializer):
    details = serializers.CharField()


class MFAMethodActivationErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class MFAMethodCodeRequestSerializer(serializers.Serializer):
    code = serializers.CharField()


class MFAMethodBackupCodeSuccessResponseSerializer(serializers.Serializer):
    backup_codes = serializers.ListSerializer(child=serializers.CharField())


class MFAMethodCodeErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()


class MFAMethodRequestCodeRequestSerializer(serializers.Serializer):
    method = serializers.CharField()


class MFAMethodPrimaryMethodChangeRequestSerializer(serializers.Serializer):
    method = serializers.CharField()
    code = serializers.CharField()
