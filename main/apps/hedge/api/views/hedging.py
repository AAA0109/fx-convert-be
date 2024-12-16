from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.core.utils.api import get_response_from_action_status, HasCompanyAssociated
from main.apps.hedge.api.service.hedging import HedgingAPIService
from main.apps.hedge.api.views.fx_forward import credit_utilization_service
from main.apps.hedge.models import HedgeSettings
from main.apps.hedge.api.serializers.whatif.autopilot import AutopilotMarginHealthResponse
from main.apps.util import ActionStatus
from main.apps.core.utils.api import validate_account_id
from rest_framework.response import Response


# ====================================================================
#  Hedging
# ====================================================================


class HedgingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    queryset = HedgeSettings.objects.all()

    @action(detail=False, methods=['get'])
    @extend_schema(
        responses={
            status.HTTP_200_OK: ActionStatusSerializer(),
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer(),
        }
    )
    def realized_pnl(self, request):
        """
        Get the realized PnL of an account
        """
        account_id = request.query_params.get('account_id', None)
        if account_id is None:
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account ID (account_id) is required!",
                    status=ActionStatus.Status.ERROR,
                ),
            )
        if not validate_account_id(request.user, account_id):
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account does not belong to user!",
                    status=ActionStatus.Status.ERROR
                )
            )
        status_acc, data = HedgingAPIService().get_realized_pnl_for_account(
            account_id=account_id
        )
        return get_response_from_action_status(
            http_status=status.HTTP_200_OK,
            action_status=status_acc,
            data=data
        )

    @extend_schema(
        responses={
            status.HTTP_200_OK: ActionStatusSerializer(),
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer(),
        }
    )
    @action(detail=False, methods=['get'])
    def unrealized_pnl(self, request):
        """
        Get the unrealized PnL of an account
        """
        account_id = request.query_params.get('account_id', None)
        if account_id is None:
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account ID (account_id) is required!",
                    status=ActionStatus.Status.ERROR,
                ),
            )
        if not validate_account_id(request.user, account_id):
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account does not belong to user!",
                    status=ActionStatus.Status.ERROR
                )
            )
        status_acc, data = HedgingAPIService().get_unrealized_pnl_for_account(
            account_id=account_id
        )

        # TODO(Nate): I am returning total unrealized PnL here, is this the right thing to do.
        total_pnl = data.total_pnl

        return get_response_from_action_status(
            http_status=status.HTTP_200_OK,
            action_status=status_acc,
            data=data
        )

    @extend_schema(
        responses={
            status.HTTP_200_OK: ActionStatusSerializer(),
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer(),
        }
    )
    @action(detail=False, methods=['get'])
    def positions(self, request):
        """
        Get all the positions for an account
        """
        account_id = request.query_params.get('account_id', None)
        if account_id is None:
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account ID (account_id) is required!",
                    status=ActionStatus.Status.ERROR,
                ),
            )
        if not validate_account_id(request.user, account_id):
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account does not belong to user!",
                    status=ActionStatus.Status.ERROR
                )
            )
        status_acc, data = HedgingAPIService().get_positions_for_account(
            account_id=account_id
        )
        return get_response_from_action_status(
            http_status=status.HTTP_200_OK,
            action_status=status_acc,
            data=data
        )

    @extend_schema(
        responses={
            status.HTTP_200_OK: ActionStatusSerializer(),
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer(),
        }
    )
    @action(detail=False, methods=['get'])
    def realized_variance(self, request):
        """
        Get realized variance for an account
        """
        account_id = request.query_params.get('account_id', None)
        if account_id is None:
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account ID (account_id) is required!",
                    status=ActionStatus.Status.ERROR,
                ),
            )
        if not validate_account_id(request.user, account_id):
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Account does not belong to user!",
                    status=ActionStatus.Status.ERROR
                )
            )
        status_acc, data = HedgingAPIService().get_realized_variance_for_account(
            account_id=account_id
        )
        return get_response_from_action_status(
            http_status=status.HTTP_200_OK,
            action_status=status_acc,
            data=data
        )


    @extend_schema(responses={status.HTTP_200_OK: AutopilotMarginHealthResponse})
    @action(detail=False, methods=["get"])
    def margin_health(self, request):
        company = request.user.company
        utilization = credit_utilization_service.get_credit_utilization(company)
        data = AutopilotMarginHealthResponse(
            {
                "credit_usage": {
                    "credit_limit": utilization.credit_limit,
                    "credit_used": utilization.credit_utilization,
                    "pnl": utilization.forward_pnl,
                },
                "margin_call_at": utilization.margin_call_at(),
            }
        )
        return Response(status=status.HTTP_200_OK, data=data.data)
