import time
import uuid
from datetime import date, datetime, timedelta

from django.shortcuts import get_object_or_404
from django.http import Http404

from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from rest_framework import mixins, viewsets, status

# perm stuff
from rest_framework.permissions import IsAuthenticated
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany

from main.apps.oems.api.serializers.execute import ExecuteGetSerializer
from main.apps.oems.models import Ticket
from main.apps.oems.backend.states import OMS_EMS_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, ERRORS
from main.apps.oems.api.utils.response import *

# ===================

class StatusViewSet(mixins.RetrieveModelMixin,
                    viewsets.GenericViewSet):

    queryset = Ticket.objects.all()
    serializer_class = ExecuteGetSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field='ticket_id'

    # =====================================================

    @extend_schema(
        summary="Status",
        description="Endpoint for retrieving ticket status by its ticket_id.",
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_202_ACCEPTED: OpenApiTypes.OBJECT,
        },
        tags=['Trading'],
        examples=[
            OpenApiExample(
                name='RFQ Status',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  'status': "DONE",
                  "action": "rfq",
                  "quote": 1.201,
                  "quote_expiry": datetime.now().isoformat(),
                  "value_date": date.today().isoformat(),
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                name='RFQ Status',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "status": "PENDING",
                  "action": "rfq",
                  "quote": None,
                  "quote_expiry": None,
                  "value_date": date.today().isoformat(),
                },
                response_only=True,
                status_codes=['202'],
            ),
            OpenApiExample(
                name='Execution Status',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "status": "DONE",
                  "action": "execute",
                  "done": 1000.,
                  "all_in_rate": 1.201,
                  "value_date": date.today().isoformat(),
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                name='Execution Status',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "status": "PENDING",
                  "action": "execute",
                  "done": None,
                  "all_in_rate": None,
                  "value_date": date.today().isoformat(),
                },
                response_only=True,
                status_codes=['202'],
            ),
            OpenApiExample(
                name='NDF Execution Status',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "status": "DONE",
                  "action": "execute",
                  "done": 1000.,
                  "all_in_rate": 1.201,
                  "value_date": (date.today()+timedelta(days=30)).isoformat(),
                  "fixing_date": (date.today()+timedelta(days=28)).isoformat(),
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                name='NDF Execution Status',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "status": "PENDING",
                  "action": "execute",
                  "done": None,
                  "all_in_rate": None,
                  "value_date": (date.today()+timedelta(days=30)).isoformat(),
                  "fixing_date": (date.today()+timedelta(days=28)).isoformat(),
                },
                response_only=True,
                status_codes=['202'],
            ),
        ]
    )
    def retrieve(self, request, *args, **kwargs):

        serializer = ExecuteGetSerializer(data=kwargs)
        serializer.is_valid(raise_exception=True)
        # headers = self.get_success_headers(serializer.data)
        instance = self.get_object()

        if instance.action == 'execute':
            data = instance.export_execute()
            if instance.internal_state == INTERNAL_STATES.PENDSETTLE:
                return Response(data, status=status.HTTP_200_OK)
            elif instance.internal_state == INTERNAL_STATES.FAILED:
                return ErrorResponse(instance.error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR, extra_data=data)
            else:
                return Response(data, status=status.HTTP_202_ACCEPTED)
        elif instance.action == 'rfq':
            data = instance.export_rfq()
            if instance.internal_state == INTERNAL_STATES.FAILED:
                return ErrorResponse(instance.error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR, extra_data=data)
            elif instance.internal_state in INTERNAL_STATES.OMS_TERMINAL_STATES:
                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response(data, status=status.HTTP_202_ACCEPTED)
        else:
            return ErrorResponse('No Ticket Found.', status=status.HTTP_404_NOT_FOUND)

    def get_object(self):
        """
        Overrides the default method to allow retrieval by `ticket_id`.
        """
        queryset = self.filter_queryset(self.get_queryset())
        key      = self.kwargs.get(self.lookup_field,'error-key')

        try:
            obj = get_object_or_404(queryset, ticket_id=key)
        except Http404:
            raise ErrorResponse('Ticket Not Found', status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(self.request, obj)
        return obj


