from rest_framework import serializers
from main.apps.hedge.models.hedgesettings import HedgeSettings


class HedgeSettingsSerializer(serializers.ModelSerializer):
    max_horizon_days = serializers.IntegerField()
    margin_budget = serializers.FloatField(allow_null=False)
    method = serializers.CharField(max_length=255)
    updated = serializers.DateTimeField(read_only=True)
    custom = serializers.JSONField(allow_null=True, default=None)
    class Meta:
        model = HedgeSettings
        fields = ['max_horizon_days', 'margin_budget', 'method', 'updated', "custom"]
