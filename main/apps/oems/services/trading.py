import functools
import logging
import traceback
import uuid
# try this first
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from typing import Optional, Union

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404

from main.apps.account.models.user import User
from main.apps.core.utils.slack import send_exception_to_slack
from main.apps.currency.models import Currency
from main.apps.oems.api.serializers.execute import ExecuteSerializer
from main.apps.oems.api.serializers.execute_rfq import ExecuteRfqSerializer
from main.apps.oems.api.serializers.req_exec_action import ReqBasicExecAction
from main.apps.oems.api.serializers.rfq import RfqSerializer, RfqRefreshSerializer
from main.apps.oems.api.utils.response import *
from main.apps.oems.backend.api import pangea_client
from main.apps.oems.backend.netting import batch_and_net
from main.apps.oems.backend.rfq_utils import do_api_rfq, do_indicative_rfq, do_pre_exec_check
from main.apps.oems.backend.states import INTERNAL_STATES, EXTERNAL_STATES, PHASES, OMS_API_ACTIONS
from main.apps.oems.backend.ticket_shared import TicketBase
from main.apps.oems.backend.xover import enqueue
from main.apps.oems.models import Ticket
from main.apps.oems.validators.ticket import route_ticket, shared_ticket_bene_validation, validate_instrument_amount
from main.apps.payment.tasks.update_cashflow_ticket_id import update_cashflow_ticket_id_task
from main.apps.oems.backend.date_utils import now

# =======

logger = logging.getLogger(__name__)


def exception_handler_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if settings.APP_ENVIRONMENT != 'local':
                tb = traceback.format_exc()
                fn = func.__name__
                logger.info(f"An error occurred in {fn}: {e}\n{tb}")
                send_exception_to_slack(e, key=fn)
                # always return 500 on error
                return INTERNAL_ERROR_RESPONSE
            else:
                raise

    return wrapper


# =======

class RfqExecutionProvider:
    queryset = Ticket.objects.all()
    MAX_WORKERS = 4

    def __init__(self):
        ...

    def get_success_headers(self, data):
        return None

    # ==============================

    def get_rfq_ticket(self, user, data) -> Union[Ticket, TicketBase]:

        ticket_id = data.get('ticket_id')
        transaction_id = data.get('transaction_id')
        company_id = user.company.id

        qry = {'company_id': company_id}

        if ticket_id:
            qry['ticket_id'] = ticket_id
        if transaction_id:
            qry['transaction_id'] = transaction_id

        obj = None
        if len(qry) > 1:
            try:
                obj = get_object_or_404(self.queryset, **qry)
            # self.check_object_permissions(self.request, obj)
            except:
                pass

        return obj

    def refresh_rfq(self, instance, data, user):

        for k, v in data.items():
            print(k, v, getattr(instance, k), type(v), type(getattr(instance, k)))
            if v is not None:
                cls_val = getattr(instance, k)
                if isinstance(cls_val, Currency):
                    cls_val = cls_val.mnemonic
                if isinstance(cls_val, uuid.UUID):
                    cls_val = str(cls_val)
                if v != cls_val:
                    return False

        instance.trader = user.id

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

    def create_rfq(self, serializer):
        ticket = serializer.save()
        ticket.life_cycle_event(f'rfq created :: {ticket.market_name} {ticket.side} {ticket.amount}')
        if ticket.cashflow_id:
            update_cashflow_ticket_id_task(ticket_id=str(ticket.ticket_id), cashflow_id=str(ticket.cashflow_id))
        return ticket

    @exception_handler_decorator
    def do_rfq(self, user, request):

        request['company'] = user.company.pk
        request['trader'] = user.id

        # TODO: if cashflow_id is provided... totally different workflow
        # TODO: could use serializer meta fields if we wanted to pull out

        if any(fld in request and request[fld] for fld in ('ticket_id', 'transaction_id')):
            # check for refresh
            serializer = RfqRefreshSerializer(data=request)
            try:
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

            # ticket_id, transaction_id, company -> company_id
            ticket = self.get_rfq_ticket(user, serializer.data)

            if not self.refresh_rfq(ticket, serializer.data, user):
                return ErrorResponse('Duplicate Transaction ID used with different parameters',
                                     status=status.HTTP_409_CONFLICT)
        else:

            request['ticket_id'] = str(uuid.uuid4())
            serializer = RfqSerializer(data=request)

            # TODO: catch the 404 and turn into our error message
            try:
                serializer.is_valid(raise_exception=True)
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

            try:
                ticket = self.create_rfq(serializer)
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        headers = self.get_success_headers(serializer.data)

        # if rfq already exists, if it has expired you can refresh
        # otherwise you don't get a new quote? do we always refresh a quote?
        # update the cashflow id

        data = ticket.export_rfq()

        if ticket.internal_state == INTERNAL_STATES.FAILED:
            data['error'] = ticket.error_message
            return ErrorResponse('internal error',
                                 status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                 extra_data=data,
                                 headers=headers)
        elif ticket.external_quote_id:
            return Response(data, status=status.HTTP_200_OK, headers=headers)
        else:
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def rfq(self, user, request):

        if isinstance(request, list):
            net_data = batch_and_net(request)
            if len(net_data) > 1:
                with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                    ret = list(executor.map(self.do_rfq, repeat(user), net_data))
            else:
                ret = []
                for req in net_data:
                    response = self.do_rfq(user, req)
                    ret.append(response)
            return MultiResponse(ret)
        else:
            return self.do_rfq(user, request)

    # ============

    @exception_handler_decorator
    def do_execute_rfq(self, user, request):

        serializer = ExecuteRfqSerializer(data=request)

        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        headers = self.get_success_headers(serializer.data)

        try:
            ticket = self.get_rfq_ticket(user, serializer.validated_data)
        except Http404:
            return ErrorResponse('Ticket Not Found', status=status.HTTP_404_NOT_FOUND)

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
            ticket.change_internal_state(INTERNAL_STATES.EXPIRED)
            ticket.change_external_state(EXTERNAL_STATES.FAILED)
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
            ticket.change_action(ticket.Actions.EXECUTE)

            exec_cfg = pangea_client.get_exec_config(market_name=ticket.market_name, company=ticket.company.id)
            if not exec_cfg:
                raise serializers.ValidationError("This market is not configured. Please contact support.")

            if serializer.validated_data.get('beneficiaries'):
                ticket.beneficiaries = serializer.validated_data['beneficiaries']
            if serializer.validated_data.get('settlement_info'):
                ticket.settlement_info = serializer.validated_data['settlement_info']

            # need to update rfq_type
            ticket.rfq_type = exec_cfg[f'{ticket.tenor}_rfq_type']
            ticket.trader = user.id

            try:
                route_ticket(ticket, exec_cfg)
                if ticket.rfq_type == Ticket.RfqType.API:
                    shared_ticket_bene_validation(ticket)
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

            try:
                self.authorize(ticket, user)
            except serializers.ValidationError as e:
                try:
                    emsg = e.detail['non_field_errors'][0]
                except:
                    emsg = 'validation failed'
                # return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

            if ticket.auth_user:

                if not do_pre_exec_check( ticket ):
                    emsg = 'pre-execution failure'
                    return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE, headers=headers)

                # change external_state, change_phase
                ticket.change_internal_state(INTERNAL_STATES.ACCEPTED)
                ticket.change_external_state(EXTERNAL_STATES.ACTIVE)
                ticket.change_phase(PHASES.PRETRADE)

                ticket.save()

                ticket.life_cycle_event(f'execute rfq created :: {ticket.market_name} {ticket.side} {ticket.amount}')

                resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id,
                               action=OMS_API_ACTIONS.EXECUTE_RFQ, source='DJANGO_APP')
                print('ENQUEUED:', resp)

                data = ticket.export_execute()

                if data['total_cost'] > 0.0:
                    # cannot happen yet
                    return Response(data, status=status.HTTP_200_OK, headers=headers)
                else:
                    return Response(data, status=status.HTTP_201_CREATED, headers=headers)
            else:
                return EXTERNAL_PANGEA_403

        else:
            data = ticket.export_rfq()
            return ErrorResponse(ticket.error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR, extra_data=data,
                                 headers=headers)

    def execute_rfq(self, user, request):
        if isinstance(request, list):
            if len(request) > 1:
                with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                    ret = list(executor.map(self.do_execute_rfq, repeat(user), request))
            else:
                ret = []
                for req in request:
                    response = self.do_execute_rfq(user, req)
                    ret.append(response)
            return MultiResponse(ret)
        else:
            return self.do_execute_rfq(user, request)

    # ============

    def create_execute(self, serializer):
        ticket = serializer.save()
        ticket.life_cycle_event(f'execution created :: {ticket.market_name} {ticket.side} {ticket.amount}')
        if ticket.cashflow_id:
            update_cashflow_ticket_id_task(ticket_id=str(ticket.ticket_id), cashflow_id=str(ticket.cashflow_id))
        return ticket

    @exception_handler_decorator
    def do_execute(self, user, request):

        request['company'] = user.company.pk
        request['trader'] = user.id
        request['ticket_id'] = str(uuid.uuid4())
        # TODO: if cashflow_id is provided... totally different workflow

        serializer = ExecuteSerializer(data=request)
        try:
            serializer.is_valid(raise_exception=True)
            instance = self.create_execute(serializer)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        try:
            self.authorize(instance, user)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            # return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        headers = self.get_success_headers(serializer.data)

        data = instance.export_execute()
        if instance.internal_state in INTERNAL_STATES.OMS_TERMINAL_STATES:
            if instance.internal_state == INTERNAL_STATES.FAILED:
                return ErrorResponse(instance.error_message, status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                     headers=headers)
            else:
                return Response(data, status=status.HTTP_200_OK, headers=headers)
        else:
            return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    def execute(self, user, request):

        if isinstance(request, list):
            net_data = batch_and_net(request)
            if len(net_data) > 1:
                with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                    ret = list(executor.map(self.do_execute, repeat(user), net_data))
            else:
                ret = []
                for req in net_data:
                    response = self.do_execute(user, req)
                    ret.append(response)
            return MultiResponse(ret)
        else:
            return self.do_execute(user, request)

    # =========

    @exception_handler_decorator
    def do_validate(self, user, request, basic=False, soft=False, serializer_class=ExecuteSerializer, ):

        request['company'] = user.company.pk
        request['trader'] = user.id

        # TODO: if cashflow_id is provided... totally different workflow

        serializer = serializer_class(data=request)

        if basic:
            serializer.basic_validation = True

        try:
            serializer.is_valid(raise_exception=(not soft))
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            if not soft:
                return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
            else:
                print(emsg)

        return Response(request, status=status.HTTP_200_OK)

    def validate(self, user, request, basic=False, soft=False):
        if isinstance(request, list):
            net_data = batch_and_net(request)
            if len(net_data) > 1:
                with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                    ret = list(executor.map(self.do_validate, repeat(user), net_data, repeat(basic), repeat(soft)))
            else:
                ret = []
                for req in net_data:
                    response = self.do_validate(user, req, basic=basic, soft=soft)
                    ret.append(response)
            return MultiResponse(ret)
        else:
            return self.do_validate(user, request, basic=basic, soft=soft)

    # =================

    def get_req_ticket(self, data):
        return get_object_or_404(self.queryset, ticket_id=data['ticket_id'])

    @exception_handler_decorator
    def do_req_action(self, action, request_data, request_user):

        # TODO: if cashflow_id is provided... totally different workflow
        # request['company'] = user.company.pk
        # request['trader'] = user.id

        serializer = ReqBasicExecAction(data=request_data)

        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        try:
            ticket = self.get_req_ticket(serializer.validated_data)
        except Http404:
            return ErrorResponse('Ticket Not Found', status=status.HTTP_404_NOT_FOUND)

        if action == OMS_API_ACTIONS.CANCEL:
            if ticket.internal_state not in INTERNAL_STATES.CANCELLABLE_STATES:
                if ticket.action == 'execute':
                    emsg = 'TOO LATE TO CANCEL'
                else:
                    emsg = 'INVALID EXECUTION TICKET'
                return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id,
                               action=OMS_API_ACTIONS.CANCEL, source='DJANGO_APP')
                print('ENQUEUED:', resp)
                # poll-id response
                data = {'poll-id': resp}
                return Response(data, status=status.HTTP_202_ACCEPTED)
        elif action == OMS_API_ACTIONS.PAUSE:
            if ticket.action != 'execute' or ticket.internal_state not in INTERNAL_STATES.PAUSEABLE_STATES:
                # HTTP_406_NOT_ACCEPTABLE
                if ticket.action == 'execute':
                    emsg = 'TOO LATE TO PAUSE'
                else:
                    emsg = 'INVALID EXECUTION TICKET'
                return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id,
                               action=OMS_API_ACTIONS.PAUSE, source='DJANGO_APP')
                print('ENQUEUED:', resp)
                # poll-id response
                data = {'poll-id': resp}
                return Response(data, status=status.HTTP_202_ACCEPTED)
        elif action == OMS_API_ACTIONS.RESUME:
            if ticket.action != 'execute' or not ticket.paused:
                # HTTP_406_NOT_ACCEPTABLE
                if ticket.action == 'execute':
                    emsg = 'TICKET NOT PAUSED'
                else:
                    emsg = 'INVALID EXECUTION TICKET'
                return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id,
                               action=OMS_API_ACTIONS.RESUME, source='DJANGO_APP')
                print('ENQUEUED:', resp)
                # poll-id response
                data = {'poll-id': resp}
                return Response(data, status=status.HTTP_202_ACCEPTED)
        elif action == OMS_API_ACTIONS.ACTIVATE:
            if ticket.action != 'execute' or ticket.internal_state not in INTERNAL_STATES.DRAFT:
                # HTTP_406_NOT_ACCEPTABLE
                if ticket.action == 'execute':
                    emsg = 'TICKET IS NOT A DRAFT'
                else:
                    emsg = 'INVALID EXECUTION TICKET'
                return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id,
                               action=OMS_API_ACTIONS.ACTIVATE, source='DJANGO_APP')
                print('ENQUEUED:', resp)
                # poll-id response
                data = {'poll-id': resp}
                return Response(data, status=status.HTTP_202_ACCEPTED)
        elif action == OMS_API_ACTIONS.AUTHORIZE:
            if ticket.action != 'execute' or ticket.auth_user:
                # HTTP_406_NOT_ACCEPTABLE
                if ticket.action == 'execute':
                    emsg = 'TICKET ALREADY AUTHORIZED'
                else:
                    emsg = 'INVALID EXECUTION TICKET'
                return ErrorResponse(emsg, status=status.HTTP_406_NOT_ACCEPTABLE)
            else:

                # TODO: check that request.user.id is authorized
                try:
                    self.authorize(ticket, request_user)
                except serializers.ValidationError as e:
                    try:
                        emsg = e.detail['non_field_errors'][0]
                    except:
                        emsg = 'validation failed'
                    # return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)
                if ticket.auth_user:
                    # DO NOT SAVE THIS ONE. LET THE OMS PROCESS IT
                    resp = enqueue(f'api2oms_{settings.APP_ENVIRONMENT}', ticket.export(), uid=ticket.id,
                                   action=OMS_API_ACTIONS.AUTHORIZE, source='DJANGO_APP')
                    print('ENQUEUED:', resp)
                    # poll-id response
                    data = {'poll-id': resp}
                    return Response(data, status=status.HTTP_202_ACCEPTED)

        else:
            raise ValueError

    def do_req_cancel(self, action: str, req: dict, user: Optional[User] = None) -> Union[Response, ErrorResponse]:
        return self.do_req_action(action=action, request_data=req, request_user=user)

    def req_cancel(self, request, user: Optional[User] = None):

        if isinstance(request, list):
            ret = []
            for req in request:
                response = self.do_req_cancel(OMS_API_ACTIONS.CANCEL, req, user)
                ret.append(response)
            return MultiResponse(ret)
        else:
            return self.do_req_cancel(OMS_API_ACTIONS.CANCEL, request, user)

    def authorize(self, ticket, user, hard=False):
        # TODO: check that user has permission for instrument + amounts

        # IF TICKET ONLY:
        try:
            validate_instrument_amount( ticket, check_company=True )
        except serializers.ValidationError as e:
            try:
                emsg = e.detail['non_field_errors'][0]
            except:
                emsg = 'validation failed'
            if hard:
                return None
                # return ErrorResponse(emsg, status=status.HTTP_400_BAD_REQUEST, code=e.status_code, extra_data=e.detail)

        if isinstance(ticket, dict):
            ticket['auth_user'] = user.id
            ticket['auth_time'] = now()
        else:
            ticket.auth_user = user.id
            ticket.auth_time = now()

        return user.id


# ======================================

trading_provider = RfqExecutionProvider()

# ======================================
