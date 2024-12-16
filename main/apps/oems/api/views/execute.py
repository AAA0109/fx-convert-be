import time
import uuid
import traceback
import logging
from datetime import date, datetime, timedelta

from django.shortcuts import get_object_or_404
from django.http import Http404

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework import mixins, viewsets, status, serializers

# perm stuff
from rest_framework.permissions import IsAuthenticated
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany

from main.apps.oems.api.serializers.execute import ExecuteSerializer, ExecuteGetSerializer, ExecuteResponseSerializer
from main.apps.oems.models import Ticket
from main.apps.oems.backend.states import OMS_EMS_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, ERRORS
from main.apps.oems.api.utils.response import *
from main.apps.core.utils.slack import send_exception_to_slack
from main.apps.oems.backend.netting import batch_and_net
from main.apps.payment.tasks.update_cashflow_ticket_id import update_cashflow_ticket_id_task
from main.apps.oems.services.trading import RfqExecutionProvider, trading_provider

from idempotency_key.decorators import idempotency_key

logger = logging.getLogger(__name__)

# ===================

class ExecuteViewSet(mixins.CreateModelMixin,
                    viewsets.GenericViewSet):

    queryset = Ticket.objects.all()
    serializer_class = ExecuteSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field='ticket_id'

    @extend_schema(
        summary="Execute Transaction",
        description="Endpoint to execute a valid RFQ or a new transaction without RFQ. Supports a list of payloads for batched requests.",
        parameters=[IdempotencyParameter],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            406: EXTERNAL_PANGEA_406,
            500: EXTERNAL_PANGEA_500,
            207: EXTERNAL_PANGEA_207,
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_201_CREATED: OpenApiTypes.OBJECT,
        },
        tags=['Trading'],
        examples=[
            OpenApiExample(
                name='Execution Request',
                value={
                  "sell_currency": "USD",
                  "buy_currency": "JPY",
                  "amount": 10000.0,
                  "lock_side": "USD",
                  "value_date": date.today().isoformat(),
                }
            ),
            OpenApiExample(
                name='Scheduled Spot Execution',
                value={
                  "sell_currency": "USD",
                  "buy_currency": "JPY",
                  "amount": 10000.0,
                  "lock_side": "USD",
                  "value_date": (date.today()+timedelta(days=10)).isoformat(),
                  "tenor": "spot",
                }
            ),
            OpenApiExample(
                name='Execution Request',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "action": "execute",
                  "value_date": date.today().isoformat(),
                  "done": 10000.,
                  "all_in_rate": 149.23,
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='Execution Request',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "action": "execute",
                  "value_date": date.today().isoformat(),
                  "done": None,
                  "all_in_rate": None,
                },
                response_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                name='NDF Execution Request',
                value={
                  "ticket_id": str(uuid.uuid4()),
                  "action": "execute",
                  "value_date": (date.today()+timedelta(days=30)).isoformat(),
                  "fixing_date": (date.today()+timedelta(days=28)).isoformat(),
                  "done": 100000.,
                  "all_in_rate": 83.23,
                },
                response_only=True,
                status_codes=['200']
            ),
        ]
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):
        return trading_provider.execute(request.user, request.data)

        if hasattr(request._request, 'data') and isinstance(request._request.data, list):
            ret = []
            net_data = batch_and_net( request._request.data )
            for rdata in net_data:
                try:
                    response = self.do_request( rdata, request._request.user )
                except Exception as e:
                    traceback.print_exc()
                    send_exception_to_slack(e, key='oems-execute')
                    response = INTERNAL_ERROR_RESPONSE
                ret.append(response)
            return MultiResponse(ret)
        elif hasattr(request._request, 'data') and isinstance(request._request.data, dict) \
            and request._request.data != {}:
            try:
                return self.do_request( request._request.data, request._request.user )
            except Exception as e:
                traceback.print_exc()
                send_exception_to_slack(e, key='oems-execute')
                return INTERNAL_ERROR_RESPONSE
        elif isinstance(request.data, list):
            ret = []
            net_data = batch_and_net( request.data )
            for rdata in net_data:
                try:
                    response = self.do_request( rdata, request.user )
                except Exception as e:
                    traceback.print_exc()
                    send_exception_to_slack(e, key='oems-execute')
                    response = INTERNAL_ERROR_RESPONSE
                ret.append(response)
            return MultiResponse(ret)
        else:
            try:
                return self.do_request( request.data, request.user )
            except Exception as e:
                traceback.print_exc()
                send_exception_to_slack(e, key='oems-execute')
                return INTERNAL_ERROR_RESPONSE

    # =====================================================

    def do_request( self, request_data, request_user ):

        request_data['company'] = request_user.company.pk
        request_data['trader'] = request_user.id

        # TODO: check if user is authorized here
        request_data['auth_user'] = request_user.id

        # TODO: if cashflow_id is provided... totally different workflow

        serializer = self.get_serializer(data=request_data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        instance = serializer.instance

        # update the cashflow id
        if instance.cashflow_id:
            update_cashflow_ticket_id_task(ticket_id=str(instance.ticket_id), cashflow_id=str(instance.cashflow_id))

        data = instance.export_execute()
        if instance.internal_state in INTERNAL_STATES.OMS_TERMINAL_STATES:
            if instance.internal_state == INTERNAL_STATES.FAILED:
                return ErrorResponse(instance.error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR, headers=headers)
            else:
                return Response(data, status=status.HTTP_200_OK, headers=headers)
        else:
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)


# ========

class BatchRequestSerializer(serializers.ListSerializer):
    child = ExecuteSerializer()

class BatchRowResponseSerializer(ExecuteSerializer):
    # Adding an extra model field
    upload_status = serializers.CharField()

    # Adding a custom computed field
    error = serializers.SerializerMethodField()

    class Meta(ExecuteSerializer.Meta):
        # Including new fields along with all fields from the base serializer
        fields = ExecuteSerializer.Meta.fields + ['upload_status', 'error']

class BatchResponseDataSerializer(serializers.ListSerializer):
    child = BatchRowResponseSerializer()

class BatchResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = BatchResponseDataSerializer()

class BatchAllorNoneExecute(mixins.CreateModelMixin,
                    viewsets.GenericViewSet):

    queryset = Ticket.objects.all()
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field='ticket_id'

    @extend_schema(
        summary="Batch Upload",
        description="Endpoint to execute a batch upload of payments.",
        request=BatchRequestSerializer,
        parameters=[IdempotencyParameter],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            500: EXTERNAL_PANGEA_500,
            status.HTTP_200_OK: BatchResponseSerializer,
        },
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):

        if hasattr(request._request, 'data') and isinstance(request._request.data, list):
            validated, data = self.validate( request._request.data )
            return Response({'success': validated, 'data': data}, status=status.HTTP_200_OK, headers=headers)
        elif isinstance(request.data, list):
            validated, data = self.validate( request.data )
            return Response({'success': validated, 'data': data}, status=status.HTTP_200_OK, headers=headers)
        else:
            return ErrorResponse('must provide a list of objects', status=status.HTTP_400_BAD_REQUEST)

    TEMPLATE_FIELDS = ['buy_currency','sell_currency','lock_side','amount','value_date','draft']

    def validate( self, data, request_user ):

        success = True
        ret = []
        todo = []

        if not data:
            success = False
            return success, ret

        for row in data:

            new_row = {}
            new_row['upload_status'] = 'SUCCESS'
            new_row['error'] = None
            new_row['serializer'] = None

            row['company'] = request_user.company.pk
            row['trader'] = request_user.id

            # TODO: check if user is authorized here
            row['auth_user'] = request_user.id

            serializer = ExecuteSerializer(data=row)

            try:
                serializer.is_valid(raise_exception=True)
                new_row['serializer'] = serializer
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                new_row['upload_status'] = 'FAILED'
                new_row['error'] = emsg
                success = False

            for fld in self.TEMPLATE_FIELDS:
                new_row[fld] = row.get(fld)

            ret.append(new_row)

        if success:
            # TODO:
            for row in ret:
                serializer = row['serializer']
                logger.info('create each ticket here', row)
                if False and serializer:
                    self.perform_create(serializer)
                    headers = self.get_success_headers(serializer.data)
                    instance = serializer.instance
                    data = instance.export_execute()
                    logger.info('create each row here')

        return success, ret

    # =====================================================


    """
    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get("data", {}), list):
            kwargs["many"] = True
        return super().get_serializer(*args, **kwargs)
    """
