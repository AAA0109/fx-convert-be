import json
import logging
import uuid

from django.db import transaction
from django.db.models import Q
from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer
from hdlib.DateTime.Date import Date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from main.apps.billing.services.what_if import FeeWhatIfService
from main.apps.core.api.serializers.error import MessageResponseSerializer
from main.apps.core.utils.api import *
from main.apps.core.utils.slack import SlackNotification
from main.apps.corpay.services.credit_utilization import CorPayCreditUtilizationService
from main.apps.hedge.api.serializers.whatif.parachute import ParachuteWhatIfResponseSerializer
from main.apps.hedge.api.service.whatif.autopilot import AutopilotWhatIf
from main.apps.hedge.api.serializers.fx_forward import DraftFxForwardSerializer, ActivateDraftFxPositionSerializer
from main.apps.hedge.api.service.whatif.parachute import ParachuteWhatIf
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition

from main.apps.hedge.api.serializers.whatif.autopilot import (
    AutopilotWhatIfResponseSerializer,
)
from main.apps.hedge.api.serializers.whatif.base import WhatIfRequestSerializer
from main.apps.hedge.services.forward_cost_service import FxQuoteServiceImpl
from main.apps.hedge.tasks import convert_forward_to_ticket
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.marketdata.services.universe_provider import UniverseProviderService
from main.apps.strategy.models.choices import Strategies

logger = logging.getLogger(__name__)
universe_provider = UniverseProviderService()
credit_utilization_service = CorPayCreditUtilizationService(universe_provider=universe_provider)
fx_quote_srvice = FxQuoteServiceImpl(universe_provider=universe_provider)
fee_what_if = FeeWhatIfService()
autopilot_what_if = AutopilotWhatIf(
    credit_utilization_service=credit_utilization_service,
    fx_quote_service=fx_quote_srvice,
    fee_what_if=fee_what_if,
    fx_spot_provider=universe_provider.fx_spot_provider
)
parachute_what_if = ParachuteWhatIf(
    credit_utilization_service=credit_utilization_service,
    fx_quote_service=fx_quote_srvice,
    fee_what_if=fee_what_if,
    fx_spot_provider=universe_provider.fx_spot_provider
)


# ====================================================================
#  Cashflows
# ====================================================================

class DraftFxForwardViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    queryset = DraftFxForwardPosition.objects.all()
    serializer_class = DraftFxForwardSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'put']

    def get_queryset(self):
        queryset = self.queryset
        qs = queryset.filter(
            Q(cashflow__account__company=self.request.user.company) |
            Q(draft_cashflow__company=self.request.user.company) |
            Q(installment__company=self.request.user.company)
        )
        return qs

    def create(self, request, *args, **kwargs) -> Response:
        company = request.user.company
        data = request.data
        data['company'] = company.id
        serializer = DraftFxForwardSerializer(data=data)
        if serializer.is_valid():
            fwd = serializer.save()
            return Response(status=status.HTTP_201_CREATED, data=serializer.data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)

    @extend_schema(
        request=ActivateDraftFxPositionSerializer,
        responses={
            status.HTTP_200_OK: DraftFxForwardSerializer
        }
    )
    @action(detail=True, methods=['put'])
    def activate(self, request, pk: int):
        serializer = ActivateDraftFxPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fwd: DraftFxForwardPosition = get_object_or_404(self.queryset, pk=pk)
        if fwd.strategy == Strategies.AUTOPILOT:
            fee = autopilot_what_if.what_if(ref_date=Date.now(), fx_forward=fwd, strategy=fwd.strategy)
        else:
            fee = parachute_what_if.what_if(ref_date=Date.now(), fx_forward=fwd, strategy=fwd.strategy)
        if fwd.status != DraftFxForwardPosition.Status.DRAFT:
            raise Exception("Cannot activate a non-draft position")

        try:
            with transaction.atomic():
                fwd.activate_cashflows()
                fwd.status = DraftFxForwardPosition.Status.PENDING_ACTIVATION
                if fwd.funding_account is None:
                    if serializer.validated_data.get("funding_account") is None:
                        raise ValidationError(
                            "No funding account is available on the draft and no funding account was in the payload"
                        )
                    fwd.funding_account = serializer.validated_data.get('funding_account')
                fwd.save()
        except Exception as e:
            logger.error(f"Error activating for cashflow: {e}")

            return get_response_from_action_status(
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                action_status=ActionStatus.error(
                    message=f"Error: failed to process Payment: {e}",
                    code='internal_server_error'
                )
            )

        # Trigger celery forward to ticket task asynchronously
        celery_task_id = uuid.uuid4()
        celery_fwd_to_ticket_task = convert_forward_to_ticket.apply_async(
            kwargs={'strategy': fwd.strategy, 'draft_fwd_position_id': fwd.pk},
            task_id=celery_task_id
        )

        # TODO: Remove this after manual trade is live
        self._send_activate_slack_messages(fwd, fee)
        return Response(status=status.HTTP_200_OK,
                        data=DraftFxForwardSerializer(fwd).data)

    def _send_activate_slack_messages(self, fwd: DraftFxForwardPosition, fee: AutopilotWhatIfResponseSerializer):
        slack = SlackNotification()
        spot_provider = FxSpotProvider()
        cashflows_to_send = []
        if fwd.installment:
            for cashflow in fwd.installment.cashflow_set.all():
                cashflows_to_send.append(cashflow)
        else:
            cashflows_to_send.append(fwd.cashflow)
        for cf in cashflows_to_send:
            risk_reduction = 1
            if hasattr(cf.account, 'hedge_settings'):
                settings = cf.account.hedge_settings
                risk_reduction = settings.custom.get('VolTargetReduction', 1.0) if settings.custom else 1.0
            if fwd.risk_reduction:
                risk_reduction = fwd.risk_reduction
            from_ccy_amount = spot_provider.convert_currency_rate(
                from_currency=cf.currency,
                to_currency=fwd.company.currency,
                amount=cf.amount
            )
            fee_json = json.dumps(fee.data, indent=4)

            message_text = f"New order for {fwd.company.name}({fwd.company.id})"
            message_mrkdwn = (
                f"from ccy: {fwd.company.currency.mnemonic}\n"
                f"from ccy amount: {from_ccy_amount * risk_reduction}\n"
                f"to ccy: {cf.currency.mnemonic}\n"
                f"to ccy amount: {cf.amount * risk_reduction}\n"
                f"lock_side: to\n"
                f"direction: {'buy' if cf.amount < 0 else 'sell'}\n"
                f"value date: {cf.date}\n"
                f"reference fwd rate: {fwd.estimated_fx_forward_price}\n"
                f"reference spot rate: {spot_provider.get_spot_value(fx_pair=fwd.fxpair, date=Date.now())}\n"
                f"fees:\n"
                f"```{fee_json}```"
            )
            slack.send_mrkdwn_message(
                text=message_text,
                mrkdwn=message_mrkdwn
            )

    @extend_schema(
        parameters=[
            WhatIfRequestSerializer
        ],
        responses={
            status.HTTP_200_OK: PolymorphicProxySerializer(
                component_name='WhatIf',
                serializers=[
                    AutopilotWhatIfResponseSerializer,
                    ParachuteWhatIfResponseSerializer
                ],
                resource_type_field_name='strategy'
            ),
            status.HTTP_400_BAD_REQUEST: MessageResponseSerializer
        })
    @action(detail=True, methods=['get'])
    def what_if(self, request, pk: int):
        serializer = WhatIfRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        fwd: DraftFxForwardPosition = get_object_or_404(self.queryset, pk=pk)
        if fwd.status != DraftFxForwardPosition.Status.DRAFT:
            raise Exception("Forward not in draft state")
        ref_date = Date.now()
        strategy = serializer.validated_data.get("strategy")
        if strategy is None:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"message": "No strategy provided."})

        if strategy == Strategies.AUTOPILOT:
            data = autopilot_what_if.what_if(ref_date=ref_date, fx_forward=fwd, strategy=strategy)
        elif strategy == Strategies.PARACHUTE:
            data = parachute_what_if.what_if(ref_date=ref_date, fx_forward=fwd, strategy=strategy)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"message": "Invalid strategy provided."})

        return Response(status=status.HTTP_200_OK, data=data.data)
