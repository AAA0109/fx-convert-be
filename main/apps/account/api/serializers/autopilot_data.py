from rest_framework import serializers

from main.apps.account.models import AutopilotData


class AutopilotDataSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    account = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AutopilotData
        fields = [
            'id',
            'account',
            'upper_limit',
            'lower_limit'
        ]


class AutopilotDataRequestSerializer(AutopilotDataSerializer):
    class Meta:
        model = AutopilotData
        fields = [
            'upper_limit',
            'lower_limit'
        ]
