from rest_framework import serializers

from main.apps.account.models import InstallmentCashflow


class InstallmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=False)
    class Meta:
        model = InstallmentCashflow
        fields = ['id', 'installment_name']
