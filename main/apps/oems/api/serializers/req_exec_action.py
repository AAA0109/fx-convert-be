import uuid

from datetime import date

from django.db import models
from django.conf import settings

from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.oems.models import Ticket

# TODO: give an example response as well
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name='Execution Action Request',
            value={
              "ticket_id": str(uuid.uuid4()),
            }
        ),
    ]
)
class ReqBasicExecAction(serializers.ModelSerializer):

    ticket_id = serializers.UUIDField(format='hex_verbose', allow_null=False)

    def validate(self, attrs):
        # Add Validation logic here
        return attrs

    class Meta:
        model = Ticket
        # These are the fields we want to expose publicly via the API
        fields = [
            'ticket_id',
        ]
