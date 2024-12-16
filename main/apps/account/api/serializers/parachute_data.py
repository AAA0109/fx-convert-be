from rest_framework import serializers

from main.apps.account.models import ParachuteData, Account


class ParachuteDataSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    account = serializers.PrimaryKeyRelatedField(read_only=True)
    safeguard = serializers.BooleanField(default=False)
    lower_p = serializers.FloatField(default=0.97)
    upper_p = serializers.FloatField(default=0.97)
    lock_lower_limit = serializers.BooleanField(default=False)

    def to_internal_value(self, data):
        if data['safeguard']:
            data['floating_pnl_fraction'] = 1
        return super().to_internal_value(data)

    def to_representation(self, instance):
        if instance.floating_pnl_fraction > 0:
            instance.safeguard = True
        return super().to_representation(instance)

    def create(self, validated_data):
        del validated_data['safeguard']
        return super().create(validated_data)

    class Meta:
        model = ParachuteData
        fields = [
            'id',
            'account',
            'lower_limit',
            'lower_p',
            'upper_p',
            'lock_lower_limit',
            'floating_pnl_fraction',
            'safeguard'
        ]


class ParachuteDataRequestSerializer(ParachuteDataSerializer):

    class Meta:
        model = ParachuteData
        fields = [
            'lower_limit',
            'lower_p',
            'upper_p',
            'lock_lower_limit',
            'floating_pnl_fraction',
            'safeguard'
        ]
