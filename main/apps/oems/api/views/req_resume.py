import uuid
import time

from datetime import datetime, date

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework import mixins, viewsets, status

from django.shortcuts import get_object_or_404
from django.conf import settings

# perm stuff
from rest_framework.permissions import IsAuthenticated
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany

from main.apps.oems.api.serializers.req_exec_action import ReqBasicExecAction
from main.apps.oems.models                          import Ticket

from main.apps.oems.backend.xover  import enqueue
from main.apps.oems.backend.states import OMS_EMS_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, ERRORS, OMS_API_ACTIONS
from main.apps.oems.api.utils.response import *

from idempotency_key.decorators import idempotency_key

# ===========

class ReqExecuteResume(mixins.CreateModelMixin,
                    viewsets.GenericViewSet):

    queryset = Ticket.objects.all()
    serializer_class = ReqBasicExecAction
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field = 'ticket_id'

    # for list mixin, use def queryset to filter. google this.

    @extend_schema(
        summary="Request Resume",
        description="Endpoint for resuming execution. Allows clients to request an execution resumption.",
        parameters=[IdempotencyParameter],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            406: EXTERNAL_PANGEA_406,
            status.HTTP_202_ACCEPTED: OpenApiTypes.OBJECT,
        },
        tags=['Execution Management'],
        examples=[
            OpenApiExample(
                name='Resume Reject',
                # description='some description'
                value={
                    'error_message': 'TICKET NOT PAUSED',
                },
                response_only=True,
                status_codes=['406'],
            ),
            OpenApiExample(
                name='Authorize Accept',
                # description='some description'
                value={
                    'poll-id': str(uuid.uuid4()),
                },
                response_only=True,
                status_codes=['202'],
            ),
        ]
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)
        self.kwargs.update(serializer.validated_data)
        ticket = self.get_object()

        if ticket.action != 'execute' or not ticket.paused:
            # HTTP_406_NOT_ACCEPTABLE
            if ticket.action == 'execute':
                emsg = 'TICKET NOT PAUSED'
            else:
                emsg = 'INVALID EXECUTION TICKET'
            return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE, headers=headers)
        else:
            resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id, action=OMS_API_ACTIONS.RESUME, source='DJANGO_APP')
            print( 'ENQUEUED:', resp )
            # poll-id response
            data = { 'poll-id': resp }
            return Response(data, status=status.HTTP_202_ACCEPTED, headers=headers)

    def get_object(self):
        """
        Overrides the default method to allow retrieval by `ticket_id`.
        """
        queryset = self.filter_queryset(self.get_queryset())
        key      = self.kwargs.get(self.lookup_field,'error-key')
        obj = get_object_or_404(queryset, ticket_id=key)
        self.check_object_permissions(self.request, obj)
        return obj
