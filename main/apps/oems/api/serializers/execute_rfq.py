import uuid

from datetime import date

from django.db import models
from django.conf import settings

from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.oems.models import Ticket

# TODO: give an example response as well
@extend_schema_serializer(
    exclude_fields=['beneficiaries','settlement_info'],
    examples=[
        OpenApiExample(
            name='Execution RFQ Request',
            value={
              "ticket_id": str(uuid.uuid4()),
            }
        ),
    ]
)
class ExecuteRfqSerializer(serializers.ModelSerializer):

    ticket_id = serializers.UUIDField(format='hex_verbose', allow_null=False)
    amount = serializers.FloatField(default=None, min_value=0.01, help_text='The amount of lock_side currency')
    settle_account_id = serializers.CharField(required=False, allow_null=True, default=None, help_text="Client-provided funding identifier. Will use default if configured. Otherwise, post-funded.")
    beneficiary_id = serializers.CharField(required=False, allow_null=True, default=None, help_text="Client-provided beneficiary identifier.")

    def validate(self, attrs):
        # Add Validation logic here
        beneficiary_id = attrs.get('beneficiary_id')
        settle_account_id = attrs.get('settlement_info')
        if beneficiary_id:
            # TODO: load bene
            ...
        if settle_account_id:
            # TODO: load settle account
            ...
        return attrs

    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'ticket_id',
            'amount',
            'settle_account_id',
            'beneficiary_id',
            'payment_memo',
            'beneficiaries',
            'settlement_info',
        ]
