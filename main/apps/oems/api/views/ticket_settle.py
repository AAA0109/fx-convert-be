import uuid
import time

from datetime import datetime, date, timedelta

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework import mixins, viewsets, status

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import Http404

# perm stuff
from rest_framework.permissions import IsAuthenticated
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany

from main.apps.oems.api.serializers.execute_rfq import ExecuteRfqSerializer
from main.apps.oems.models                      import Ticket

from main.apps.oems.backend.xover  import enqueue
from main.apps.oems.backend.states import OMS_EMS_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, ERRORS, OMS_API_ACTIONS
from main.apps.oems.api.utils.response import ErrorResponse, Response

from idempotency_key.decorators import idempotency_key

# ===========

class TicketSettleView(mixins.CreateModelMixin,
                    viewsets.GenericViewSet):

    queryset = Ticket.objects.all()
    serializer_class = ExecuteRfqSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field = 'ticket_id'

    def check_object_permissions(self, request, obj):
        if request.user.company != obj.company:
            raise PermissionDenied(detail="") # no detail so we do not leak?

    @extend_schema(
        summary="Settle Transaction",
        description="Endpoint for ticket settlement information.",
        parameters=[
            OpenApiParameter(
                name='x-idempotency-key',
                description='Optional idempotency key to handle network disruptions. Max 255 characters. We recommend uuid4.',
                required=False,
                type=str,
                location=OpenApiParameter.HEADER,
            ),
        ],
        responses={
            status.HTTP_406_NOT_ACCEPTABLE: OpenApiTypes.OBJECT,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_201_CREATED: OpenApiTypes.OBJECT,
            status.HTTP_202_ACCEPTED: OpenApiTypes.OBJECT,
        },
        tags=['Trading'],
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)
        self.kwargs.update(serializer.validated_data)

        try:
            ticket = self.get_object()
        except Http404:
            raise ErrorResponse('Ticket Not Found', status=status.HTTP_404_NOT_FOUND)

        if False:
            # HTTP_406_NOT_ACCEPTABLE
            emsg = 'execution unfinished' # technically you can settle stuff before execution finishes
            return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE, headers=headers)
        elif True:
            # cannot happen yet
            data = None
            # patch the settlement here
            return Response(data, status=status.HTTP_200_OK, headers=headers)
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            data = None
            return ErrorResponse(ticket.error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR, extra_data=data, headers=headers)

    # =============================

    def get_object(self):
        """
        Overrides the default method to allow retrieval by `ticket_id`.
        """
        queryset = self.filter_queryset(self.get_queryset())
        key      = self.kwargs.get(self.lookup_field,'error-key')
        obj = get_object_or_404(queryset, ticket_id=key)
        self.check_object_permissions(self.request, obj)
        return obj
