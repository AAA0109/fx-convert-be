import logging

from django.db import transaction
from rest_framework import serializers

logger = logging.getLogger(__name__)
from main.apps.corpay.models import ManualForwardRequest
from main.apps.currency.models import FxPair


class UpdateNDFSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualForwardRequest
        fields = [
            'id',
            'created',
            'modified',
            'request',
            'pair',
            'amount',
            'delivery_date'
        ]

    pair = serializers.PrimaryKeyRelatedField(queryset=FxPair.objects.all(), required=True)

    @transaction.atomic
    def create(self, validated_data):
        request = ManualForwardRequest(
            **validated_data,
        )
        request.save()
        return request
