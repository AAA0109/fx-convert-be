import uuid
import time
import traceback
import logging

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
from main.apps.oems.api.utils.response import *
from main.apps.oems.backend.api import pangea_client
from main.apps.oems.validators.ticket import route_ticket, shared_ticket_bene_validation
from main.apps.oems.backend.fields import EXEC_RFQ_RETURN_FIELDS
from idempotency_key.decorators import idempotency_key
from main.apps.core.utils.slack import send_exception_to_slack
from main.apps.oems.services.trading import RfqExecutionProvider, trading_provider

# ===========

logger = logging.getLogger(__name__)

class ExecuteRfqViewSet(mixins.CreateModelMixin,
                    viewsets.GenericViewSet):

    queryset = Ticket.objects.all()
    serializer_class = ExecuteRfqSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field = 'ticket_id'

    # for list mixin, use def queryset to filter. google this.

    @extend_schema(
        summary="Execute Quote",
        description="Endpoint for RFQ Execution. Allows clients to execute an RFQ ticket. Supports a list of payloads for batched requests.",
        parameters=[IdempotencyParameter],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            406: EXTERNAL_PANGEA_406,
            410: EXTERNAL_PANGEA_410,
            500: EXTERNAL_PANGEA_500,
            207: EXTERNAL_PANGEA_207,
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_201_CREATED: OpenApiTypes.OBJECT,
            status.HTTP_202_ACCEPTED: OpenApiTypes.OBJECT,
        },
        tags=['Trading'],
        examples=[
            OpenApiExample(
                name='Execute Rejected',
                # description='some description'
                value={
                    'ticket_id': str(uuid.uuid4()),
                    'action': 'execute',
                    'status': 'FAILED',
                    'quote_expiry': datetime.now().isoformat(),
                    'error_message': 'QUOTE EXPIRED',
                },
                response_only=True,
                status_codes=['410'],
            ),
            OpenApiExample(
                name='Execute Failed',
                # description='some description'
                value={
                    'error_message': 'already executing',
                },
                response_only=True,
                status_codes=['406'],
            ),
            OpenApiExample(
                name='Rfq Pending',
                # description='some description'
                value={
                    'ticket_id': str(uuid.uuid4()),
                    'status': 'PENDING',
                    'action': 'execute',
                    'status': 'PENDING',
                    'quote_expiry': None,
                    'message': 'WAITING FOR RFQ',
                },
                response_only=True,
                status_codes=['202'],
            ),
            OpenApiExample(
                name='Execute Accepted',
                # description='some description'
                value={
                    'ticket_id': str(uuid.uuid4()),
                    'action': 'execute',
                    'status': 'PENDING',
                    'value_date': date.today().isoformat(),
                    'done': None,
                    'all_in_rate': None,
                },
                response_only=True,
                status_codes=['201'],
            ),
            OpenApiExample(
                name='Execute Ready',
                # description='some description'
                value={
                    'ticket_id': str(uuid.uuid4()),
                    'action': 'execute',
                    'status': 'DONE',
                    'value_date': date.today().isoformat(),
                    'done': 1000.,
                    'all_in_rate': 1.2,
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                name='NDF Execute Ready',
                # description='some description'
                value={
                    'ticket_id': str(uuid.uuid4()),
                    'action': 'execute',
                    'status': 'DONE',
                    'value_date': (date.today()+timedelta(days=30)).isoformat(),
                    'fixing_date': (date.today()+timedelta(days=28)).isoformat(),
                    'done': 100000.,
                    'all_in_rate': 83.12,
                },
                response_only=True,
                status_codes=['200'],
            )
        ]
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):

        return trading_provider.execute_rfq(request.user, request.data)
        
        if hasattr(request._request, 'data') and isinstance(request._request.data, list):
            ret = []
            for rdata in request._request.data:
                try:
                    response = self.do_request( rdata, request._request.user )
                except Exception as e:
                    traceback.print_exc()
                    send_exception_to_slack(e, key='oems-rfq-exec')
                    response = INTERNAL_ERROR_RESPONSE
                ret.append(response)
            return MultiResponse(ret)
        elif hasattr(request._request, 'data') and isinstance(request._request.data, dict) \
            and request._request.data != {}:
            try:
                return self.do_request( request._request.data, request._request.user )
            except Exception as e:
                traceback.print_exc()
                send_exception_to_slack(e, key='oems-rfq-exec')
                return INTERNAL_ERROR_RESPONSE
        elif isinstance(request.data, list):
            ret = []
            for rdata in request.data:
                try:
                    response = self.do_request( rdata, request.user )
                except Exception as e:
                    traceback.print_exc()
                    send_exception_to_slack(e, key='oems-rfq-exec')
                    response = INTERNAL_ERROR_RESPONSE
                ret.append(response)
            return MultiResponse(ret)
        else:
            try:
                return self.do_request( request.data, request.user )
            except Exception as e:
                traceback.print_exc()
                send_exception_to_slack(e, key='oems-rfq-exec')
                return INTERNAL_ERROR_RESPONSE

    def do_request( self, request_data, request_user ):

        serializer = self.get_serializer(data=request_data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        headers = self.get_success_headers(serializer.data)
        self.kwargs.update(serializer.validated_data)

        try:
            ticket = self.get_object()
        except Http404:
            raise ErrorResponse('Ticket Not Found', status=status.HTTP_404_NOT_FOUND)

        if ticket.action != Ticket.Actions.RFQ:
            # HTTP_406_NOT_ACCEPTABLE
            if ticket.action == Ticket.Actions.EXECUTE:
                emsg = 'already executing'
            else:
                emsg = 'not rfq ticket'
            return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE, headers=headers)
        elif not ticket.external_quote_expiry:
            data = ticket.export_rfq()
            data['message'] = 'WAITING FOR RFQ'
            return Response(data, status=status.HTTP_202_ACCEPTED, headers=headers)
        elif ticket.is_expired():
            ticket.change_internal_state( INTERNAL_STATES.EXPIRED )
            ticket.change_external_state( EXTERNAL_STATES.FAILED )
            data = ticket.export_rfq()
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
            ticket.change_action( ticket.Actions.EXECUTE )

            exec_cfg = pangea_client.get_exec_config(market_name=ticket.market_name, company=ticket.company.id)
            if not exec_cfg:
                raise serializers.ValidationError("This market is not configured. Please contact support.")

            # TODO: if beneficiary + settlement_info in validated_data, validate benes
            if serializer.validated_data.get('beneficiaries'):
                ticket.beneficiaries = serializer.validated_data['beneficiaries']
            if serializer.validated_data.get('settlement_info'):
                ticket.settlement_info = serializer.validated_data['settlement_info']

            # need to update rfq_type
            ticket.rfq_type = exec_cfg[f'{ticket.tenor}_rfq_type']
            
            try:
                route_ticket( ticket, exec_cfg )
                if ticket.rfq_type == Ticket.RfqType.API:
                    shared_ticket_bene_validation( ticket )
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

            # change external_state, change_phase
            ticket.change_internal_state( INTERNAL_STATES.ACCEPTED )
            ticket.change_external_state( EXTERNAL_STATES.ACTIVE )
            ticket.change_phase( PHASES.PRETRADE )

            # TODO: check if user is authorized here
            ticket.auth_user = request_user.id
            ticket.save()

            logger.info( f'creating execute_rfq ticket: {ticket.export()}')
            resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id, action=OMS_API_ACTIONS.EXECUTE_RFQ, source='DJANGO_APP')
            logger.error( 'ENQUEUED: {resp}' )

            data = ticket.export_execute()

            if data['total_cost'] != 0.0:
                # cannot happen yet
                return Response(data, status=status.HTTP_200_OK, headers=headers)
            else:
                return Response(data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            data = ticket.export_rfq()
            return ErrorResponse(ticket.error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR, extra_data=data, headers=headers)

    def get_object(self):
        """
        Overrides the default method to allow retrieval by `ticket_id`.
        """
        queryset = self.filter_queryset(self.get_queryset())
        key      = self.kwargs.get(self.lookup_field,'error-key')

        obj = get_object_or_404(queryset, ticket_id=key)

        self.check_object_permissions(self.request, obj)

        return obj

