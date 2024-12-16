import logging

from django.db import transaction
from rest_framework import serializers

from main.apps.account.models import Company, User
from main.apps.corpay.models import UpdateRequest

logger = logging.getLogger(__name__)


class UpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = UpdateRequest
        fields = [
            'id',
            'created',
            'modified',
            'type',
            'request_details',
            'status',
            'company',
            'user',
        ]

    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False)
    status = serializers.CharField(required=False, read_only=True)

    @transaction.atomic
    def create(self, validated_data):
        request = UpdateRequest(
            **validated_data,
            status=UpdateRequest.RequestStatus.NEW,
            company=validated_data['user'].company,
        )
        request.save()
        return request
