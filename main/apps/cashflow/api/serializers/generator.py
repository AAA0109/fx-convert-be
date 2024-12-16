from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from main.apps.cashflow.models import CashFlowGenerator
from main.apps.core.constants import CURRENCY_HELP_TEXT, LOCK_SIDE_HELP_TEXT
from main.apps.currency.models import Currency
from main.apps.strategy.models import HedgingStrategy


# ====================================================================
#  CashFlow serializers
# ====================================================================


class CashFlowGeneratorSerializer(serializers.ModelSerializer):
    """
    A serializer for the DraftCashFlow model.

    Note that date fields should be be in the format YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]
    """
    status = serializers.CharField(
        read_only=True
    )
    sell_currency = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all(),
        help_text=CURRENCY_HELP_TEXT
    )
    buy_currency = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all(),
        help_text=CURRENCY_HELP_TEXT
    )
    lock_side = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all(),
        help_text=LOCK_SIDE_HELP_TEXT
    )
    is_draft = serializers.BooleanField(
        required=True,
        help_text='“true” = cashflow is a draft, “false” = cashflow is approved and executable'
    )

    class Meta:
        model = CashFlowGenerator
        fields = [
            'cashflow_id',
            'status',
            'name',
            'description',
            "buy_currency",
            "sell_currency",
            "lock_side",
            "amount",
            'value_date',
            'is_draft',
            'created',
            'modified',
        ]

        read_only_fields = ['id', 'created', 'modified']

    def validate_amount(self, value):
        if value == 0:
            raise serializers.ValidationError(f"Cash flow amount cannot be zero")
        return value

    def to_representation(self, instance):
        instance.is_draft = instance.status == CashFlowGenerator.Status.DRAFT
        representation = super().to_representation(instance)
        return representation

    def create(self, validated_data):
        is_draft = validated_data.pop('is_draft', False)
        status = CashFlowGenerator.Status.DRAFT if is_draft else CashFlowGenerator.Status.PENDING
        instance = CashFlowGenerator.objects.create(status=status, **validated_data)
        return instance
