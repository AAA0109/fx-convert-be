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
from rest_framework.views import APIView
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany

from main.apps.oems.api.serializers.fund import FundTransactionSerializer
from main.apps.oems.models                      import Ticket

from main.apps.oems.backend.states import OMS_EMS_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, ERRORS, OMS_API_ACTIONS
from main.apps.oems.api.utils.response import *
from main.apps.oems.backend.api import pangea_client
from idempotency_key.decorators import idempotency_key


# ===========

class FundTransactionViewSet(mixins.CreateModelMixin,
                    viewsets.GenericViewSet):

    queryset = Ticket.objects.all()
    serializer_class = FundTransactionSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field = 'ticket_id'

    # for list mixin, use def queryset to filter. google this.

    @extend_schema(
        summary="Fund Transaction",
        description="Fund a spot or forward payment transaction.",
        parameters=[IdempotencyParameter],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            406: EXTERNAL_PANGEA_406,
            207: EXTERNAL_PANGEA_207,
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_202_ACCEPTED: OpenApiTypes.OBJECT,
        },
        tags=['Trading'],
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):

        if False and hasattr(request._request, 'data') and isinstance(request._request.data, list):
            ret = []
            for rdata in request._request.data:
                response = self.do_request( rdata, request._request.user )
                ret.append(response)
            return MultiResponse(ret)
        elif False and hasattr(request._request, 'data') and isinstance(request._request.data, dict) \
            and request._request.data != {}:
            return self.do_request( request._request.data, request._request.user )
        elif False and isinstance(request.data, list):
            ret = []
            for rdata in request.data:
                response = self.do_request( rdata, request.user )
                ret.append(response)
            return MultiResponse(ret)
        else:
            return self.do_request( request.data, request.user )

        return self.do_request( request.data, request.user )

    def do_request( self, request_data, request_user ):

        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)
        self.kwargs.update(serializer.validated_data)

        try:
            ticket = self.get_object()
        except Http404:
            raise ErrorResponse('Ticket Not Found', status=status.HTTP_404_NOT_FOUND)

        return ErrorResponse('Not implemented yet...', status=status.HTTP_500_INTERNAL_SERVER_ERROR, headers=headers)


        """
        if ticket.action != Ticket.Actions.RFQ:
            # HTTP_406_NOT_ACCEPTABLE
            if ticket.action == Ticket.Actions.EXECUTE:
                emsg = 'already executing'
            else:
                emsg = 'not rfq ticket'
            return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE, headers=headers)
        elif not ticket.external_quote_expiry:
            data = ticket.export_fields(RFQ_RETURN_FIELDS)
            data['message'] = 'WAITING FOR RFQ'
            return Response(data, status=status.HTTP_202_ACCEPTED, headers=headers)
        elif ticket.is_expired():
            ticket.change_internal_state( INTERNAL_STATES.EXPIRED )
            ticket.change_external_state( EXTERNAL_STATES.FAILED )
            data = ticket.export_fields(RFQ_RETURN_FIELDS)
            return ErrorResponse('QUOTE EXPIRED', status=status.HTTP_410_GONE, extra_data=data, headers=headers)
        elif ticket.internal_state == INTERNAL_STATES.RFQ_DONE:
            if ticket.amount is None:
                amount = serializer.validated_data['amount']
                if amount is None:
                    emsg = 'no amount provided'
                    return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE, headers=headers)
                else:
                    ticket.amount = amount

            ticket.destination = None
            ticket.action      = ticket.Actions.EXECUTE

            exec_cfg = pangea_client.get_exec_config(market_name=ticket.market_name, company=ticket.company.id)
            if not exec_cfg:
                raise serializers.ValidationError("This market is not configured. Please contact support.")

            # TODO: if beneficiary + settlement_info in validated_data, validate benes

            route_ticket( ticket, exec_cfg )

            # change external_state, change_phase
            ticket.change_internal_state( INTERNAL_STATES.ACCEPTED )
            ticket.change_external_state( EXTERNAL_STATES.ACTIVE )
            ticket.change_phase( PHASES.PRETRADE )

            # TODO: check if user is authorized here
            ticket.auth_user   = request_user.id
            ticket.save()

            resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id, action=OMS_API_ACTIONS.EXECUTE_RFQ, source='DJANGO_APP')
            print( 'ENQUEUED:', resp )
        """

    def get_object(self):
        """
        Overrides the default method to allow retrieval by `ticket_id`.
        """
        queryset = self.filter_queryset(self.get_queryset())
        key      = self.kwargs.get(self.lookup_field,'error-key')

        obj = get_object_or_404(queryset, ticket_id=key)

        self.check_object_permissions(self.request, obj)

        return obj

