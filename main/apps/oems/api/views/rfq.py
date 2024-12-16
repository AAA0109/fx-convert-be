import logging
import traceback
import uuid
from datetime import date, datetime, timedelta

from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from idempotency_key.decorators import idempotency_key
from rest_framework import mixins, viewsets, status, serializers
# perm stuff
from rest_framework.permissions import IsAuthenticated

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.currency.models import Currency
from main.apps.oems.api.serializers.rfq import RfqSerializer, RfqRefreshSerializer
from main.apps.oems.api.utils.response import *
from main.apps.oems.backend.rfq_utils import do_api_rfq, do_indicative_rfq
from main.apps.oems.backend.states import INTERNAL_STATES, EXTERNAL_STATES, PHASES
from main.apps.oems.models import Ticket
from main.apps.core.utils.slack import send_exception_to_slack
from main.apps.oems.backend.netting import batch_and_net
from main.apps.payment.tasks.update_cashflow_ticket_id import update_cashflow_ticket_id_task
from main.apps.oems.services.trading import RfqExecutionProvider, trading_provider

# ===================
logger = logging.getLogger(__name__)


class RfqViewSet(mixins.CreateModelMixin,
                 viewsets.GenericViewSet):
    queryset = Ticket.objects.all()
    serializer_class = RfqSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    lookup_field = 'transaction_id'
    lookup_field2 = 'company'
    lookup_field3 = 'ticket_id'

    # TODO: UserBelongsToCompany

    # for list mixin, use def queryset to filter. google this.
    @extend_schema(
        summary="Request Quote",
        description="Endpoint for creating or refreshing a Request for Quote. Allows you to get an executable exchange rate without entering into a transaction. Supports a list of payloads for batched requests.",
        parameters=[IdempotencyParameter],
        responses={
            400: EXTERNAL_PANGEA_400,
            401: EXTERNAL_PANGEA_401,
            403: EXTERNAL_PANGEA_403,
            404: EXTERNAL_PANGEA_404,
            406: EXTERNAL_PANGEA_406,
            409: EXTERNAL_PANGEA_409,
            500: EXTERNAL_PANGEA_500,
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_201_CREATED: OpenApiTypes.OBJECT,
            207: EXTERNAL_PANGEA_207,
        },
        tags=['Trading'],
        examples=[
            OpenApiExample(
                name='RFQ Request',
                value={
                    "sell_currency": "USD",
                    "buy_currency": "JPY",
                    "amount": 10000.0,
                    "lock_side": "USD",
                    "value_date": date.today().isoformat(),
                }
            ),
            OpenApiExample(
                name='NDF RFQ Request',
                value={
                    "sell_currency": "USD",
                    "buy_currency": "INR",
                    "amount": 100000.0,
                    "lock_side": "USD",
                    "value_date": date.today().isoformat(),
                }
            ),
            OpenApiExample(
                name='RFQ Request',
                value={
                    "ticket_id": str(uuid.uuid4()),
                    "action": "rfq",
                    "quote": 1.2,
                    "quote_expiry": datetime.now().isoformat(),
                    "value_date": date.today().isoformat(),
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='RFQ Request',
                value={
                    "ticket_id": str(uuid.uuid4()),
                    "action": "rfq",
                    "quote": None,
                    "quote_expiry": None,
                    "value_date": date.today().isoformat(),
                },
                response_only=True,
                status_codes=['201']
            ),
            OpenApiExample(
                name='NDF RFQ Request',
                value={
                    "ticket_id": str(uuid.uuid4()),
                    "action": "rfq",
                    "quote": 1.2,
                    "quote_expiry": datetime.now().isoformat(),
                    "value_date": (date.today() + timedelta(days=30)).isoformat(),
                    "fixing_date": (date.today() + timedelta(days=28)).isoformat(),
                },
                response_only=True,
                status_codes=['200']
            ),
            OpenApiExample(
                name='MDF RFQ Request',
                value={
                    "ticket_id": str(uuid.uuid4()),
                    "action": "rfq",
                    "quote": None,
                    "quote_expiry": None,
                    "value_date": (date.today() + timedelta(days=30)).isoformat(),
                    "fixing_date": (date.today() + timedelta(days=28)).isoformat(),
                },
                response_only=True,
                status_codes=['201']
            ),
        ]
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):
        return trading_provider.rfq(request.user, request.data)

        if hasattr(request._request, 'data') and isinstance(request._request.data, list):
            user = request._request.user

            return 
            ret = []
            net_data = batch_and_net( request._request.data )
            for rdata in net_data:
                try:
                    response = self.do_request(rdata, request._request.user)
                except Exception as e:
                    traceback.print_exc()
                    send_exception_to_slack(e, key='oems-rfq')
                    response = INTERNAL_ERROR_RESPONSE
                ret.append(response)
            return MultiResponse(ret)
        elif hasattr(request._request, 'data') and isinstance(request._request.data, dict) \
            and request._request.data != {}:
            try:
                return self.do_request(request._request.data, request._request.user)
            except Exception as e:
                traceback.print_exc()
                send_exception_to_slack(e, key='oems-rfq')
                return INTERNAL_ERROR_RESPONSE
        elif isinstance(request.data, list):
            ret = []
            net_data = batch_and_net( request.data )
            for rdata in net_data:
                try:
                    response = self.do_request(rdata, request.user)
                except Exception as e:
                    traceback.print_exc()
                    send_exception_to_slack(e, key='oems-rfq')
                    response = INTERNAL_ERROR_RESPONSE 
                ret.append(response)
            return MultiResponse(ret)
        else:
            try:
                return self.do_request(request.data, request.user)
            except Exception as e:
                traceback.print_exc()
                send_exception_to_slack(e, key='oems-rfq')
                return INTERNAL_ERROR_RESPONSE
                
    def do_request(self, request_data, request_user):

        request_data['company'] = request_user.company.pk
        request_data['trader'] = request_user.id

        # TODO: if cashflow_id is provided... totally different workflow

        try:
            if (self.lookup_field not in request_data or not request_data[self.lookup_field]) and (
                self.lookup_field3 not in request_data or not request_data[self.lookup_field3]):
                raise Http404()
            serializer = RfqRefreshSerializer(data=request_data)
            serializer.is_valid(raise_exception=True)
            self.kwargs['ticket_id'] = serializer.data['ticket_id']
            self.kwargs['transaction_id'] = serializer.data['transaction_id']
            self.kwargs['company'] = request_user.company.id
            ticket = self.get_object()
            headers = self.get_success_headers(serializer.data)
            if not self.perform_refresh(ticket, serializer.data, request_user):
                return ErrorResponse('Duplicate ticket_id used with different parameters. Create a new request to proceed.',
                                     status=status.HTTP_409_CONFLICT, headers=headers)
        except Http404:
            ticket = None

        if ticket is None:
            serializer = self.get_serializer(data=request_data)

            try:
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
            except Exception as e:
                return ErrorResponse('internal error',
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                self.perform_create(serializer)
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
            except Exception as e:
                return ErrorResponse('internal error',
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            headers = self.get_success_headers(serializer.data)
            ticket = serializer.instance

            # update the cashflow id
            if ticket.cashflow_id:
                update_cashflow_ticket_id_task(ticket_id=str(ticket.ticket_id), cashflow_id=str(ticket.cashflow_id))

        # if rfq already exists, if it has expired you can refresh
        # otherwise you don't get a new quote? do we always refresh a quote?

        data = ticket.export_rfq()

        if ticket.internal_state == INTERNAL_STATES.FAILED:
            return ErrorResponse('internal error',
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                 extra_data=data,
                                 headers=headers)
        elif ticket.external_quote_id:
            return Response(data, status=status.HTTP_200_OK, headers=headers)
        else:
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    # ================================

    def perform_refresh(self, instance, data, request_user):

        for k, v in data.items():
            logger.info( f'{k} {v} {getattr(instance,k)} {type(v)} {type(getattr(instance,k))}')
            if v is not None:
                cls_val = getattr(instance, k)
                if isinstance(cls_val, Currency):
                    cls_val = cls_val.mnemonic
                if isinstance(cls_val, uuid.UUID):
                    cls_val = str(cls_val)
                if v != cls_val:
                    return False

        instance.trader = request_user.id

        # initialize states
        instance.change_internal_state(INTERNAL_STATES.DRAFT if instance.draft else INTERNAL_STATES.NEW)
        instance.change_external_state(EXTERNAL_STATES.PENDING)
        instance.change_phase(PHASES.PRETRADE)

        if instance.rfq_type == Ticket.RfqType.API:  # TODO: check if market needs a manual rfq
            if do_api_rfq(instance):
                instance.save()
        elif instance.rfq_type == Ticket.RfqType.INDICATIVE:
            if do_indicative_rfq(instance):
                instance.save()

        return instance

    def get_object(self):
        """
        Overrides the default method to allow retrieval by `ticket_id`.
        """
        queryset = self.filter_queryset(self.get_queryset())
        qry = {
            'company_id': self.kwargs.get(self.lookup_field2, -1),
        }
        try:
            qry['transaction_id'] = self.kwargs[self.lookup_field]
        except KeyError:
            pass
        try:
            qry['ticket_id'] = self.kwargs[self.lookup_field3]
        except KeyError:
            pass
        obj = get_object_or_404(queryset, **qry)
        self.check_object_permissions(self.request, obj)
        return obj

        
