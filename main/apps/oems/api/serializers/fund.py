import uuid

from datetime import date

from django.db import models
from django.conf import settings

from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.currency.models.currency import Currency
from main.apps.account.models import Company
from main.apps.core.constants import CURRENCY_HELP_TEXT
from main.apps.oems.models                      import Ticket

# ====

@extend_schema_serializer(
    exclude_fields=[],
    examples=[
        OpenApiExample(
            name='Fund Transaction Request',
            value={
              "ticket_id": str(uuid.uuid4()),
              "funding_type": "bank_transfer",
              "source_account": None,
              "source_amount": 100.0,
              "source_ccy": "USD",
            }
        ),
    ]
)
class FundTransactionSerializer(serializers.ModelSerializer):

    class FundingTypes(models.TextChoices):
        DIRECT_DEBIT = 'direct_debit', 'direct_debit'
        WIRE = 'wire', 'wire'
        BANK_TRANSFER = 'bank_transfer', 'bank_transfer'
        WALLET_TRANSFER = 'wallet_transfer', 'wallet_transfer'

    ticket_id = serializers.UUIDField(format='hex_verbose', allow_null=False)
    funding_type = serializers.ChoiceField(choices=FundingTypes.choices, default=FundingTypes.BANK_TRANSFER)
    source_id = serializers.CharField(required=True)
    source_amount = serializers.FloatField(default=None, min_value=0.01, help_text='The amount of currency')
    source_ccy = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),help_text=CURRENCY_HELP_TEXT)

    def validate(self, attrs):
        # Add Validation logic here
        return attrs

    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'ticket_id',
            'funding_type',
            'source_id',
            'source_amount',
            'source_ccy',
        ]
