from typing import Iterable

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet

from main.apps.account.api.serializers.account import CreateAccountForCompanyViewSerializer, AccountSerializer, \
    HedgePolicyForAccountViewSerializer, HedgeSettingsSerializer
from main.apps.account.api.services.customer import CustomerAPIService
from main.apps.account.models import Account
from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.core.utils.api import *
from main.apps.currency.models import CurrencyTypes
from main.apps.util import ActionStatus


# ====================================================================
#  Account management.
# ====================================================================


class AccountViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    queryset = Account.objects.all().filter(is_hidden=False)

    @extend_schema(
        responses={
            status.HTTP_200_OK: AccountSerializer(many=True)
        }
    )
    def list(self, request):
        """
        Get all the accounts of a company
        """
        accounts = self.queryset.filter(
            company=request.user.company
        ).prefetch_related(
            'hedge_settings',
            'autopilot_data',
            'parachute_data'
        )
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=CreateAccountForCompanyViewSerializer,
        responses={
            status.HTTP_201_CREATED: AccountSerializer,
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: ActionStatusSerializer
        }
    )
    def create(self, request):
        """
        Create an account for a company

        Optionally, the account can be created with some raw and / or recurring
        cashflows. If these are not provided, a list of currencies that the account is allowed to trade in must be
        provided. It is permissible to provide both the currencies list *and* cashflows.
        """
        company_id: int = request.user.company.pk

        serializer = CreateAccountForCompanyViewSerializer(data=request.data, user=request.user)

        # Always handle exceptional cases first (Go-style)
        if not serializer.is_valid():
            return get_response_from_action_status(
                data=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus(
                    message="Error: Bad Request",
                    status=ActionStatus.Status.ERROR,
                ),
            )

        account_name: str = serializer.data.get('account_name')
        currencies: Optional[Iterable[CurrencyTypes]] = serializer.data.get('currencies')
        if currencies:
            currencies = [cny.upper() for cny in currencies]

        account_type: Account.AccountType = serializer.get_account_type()
        is_active: bool = serializer.data.get('is_active')

        account = CustomerAPIService().create_account_for_company(
            company_id=company_id,
            account_name=account_name,
            currencies=currencies,
            account_type=account_type,
            is_active=is_active)

        serializer = AccountSerializer(account)
        data = serializer.data

        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            status.HTTP_200_OK: AccountSerializer,
            status.HTTP_404_NOT_FOUND: ActionStatusSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: ActionStatusSerializer
        }
    )
    @action(detail=True, methods=['put'])
    def activate(self, request, pk: int):
        """
        Activate an account
        """
        queryset = Account.get_account_objs(company=request.user.company_id, active_only=False)
        account = get_object_or_404(queryset, pk=pk)

        account_obj = CustomerAPIService().activate_account(
            account=account
        )

        return Response(AccountSerializer(account_obj).data)

    @extend_schema(
        responses={
            status.HTTP_200_OK: AccountSerializer,
        }
    )
    @action(detail=True, methods=['put'])
    def deactivate(self, request, pk: int):
        """
        Deactivate an account
        """

        queryset = Account.get_account_objs(company=request.user.company_id, active_only=False)
        account = get_object_or_404(queryset, pk=pk)

        account_obj = CustomerAPIService().deactivate_account(
            account=account,
        )

        return Response(AccountSerializer(account_obj).data)

    @extend_schema(
        request=HedgePolicyForAccountViewSerializer,
        responses={
            status.HTTP_200_OK: HedgeSettingsSerializer,
        }
    )
    @action(detail=True, methods=['post'])
    def set_hedge_policy(self, request, pk: int):
        """
        Set an account's hedge policy
        <br />
        <br />
        <b>method</b> - the hedge method to use for this account
        <br />
        <b>margin_budget</b> - float, the maximum daily margin exposure allowed (in units of account's domestic currency)
        <br />
        <b>max_horizon</b> - the maximum number of days into the future to hedge for this account (ie,
        cashflows beyond this are not taking into account, until they enter this horizon)
        <br />
        <b>custom:</b>
        <br />
        <b>vol_target_reduction</b> - number between [0,1], where 0 means they have no risk reduction,
        1.0 means 100% risk reduction.
        <br />
        <b>var_95_exposure_ratio</b> - this is what percentage of the account value that they don't want their 95% VaR
        to exceed.
        <br />
        <b>var_95_exposure_window</b> - the number of days we lookback when computing PnL to determine how much the
        account has lost/gained ... the VaR bound won't kick in until the PnL starts to near it, at which point we will
        put on a position to lock in their losses
        """
        queryset = Account.get_account_objs(company=request.user.company_id, active_only=False)
        _ = get_object_or_404(queryset, pk=pk)

        serializer = HedgePolicyForAccountViewSerializer(data=request.data, user=request.user)
        serializer.is_valid(raise_exception=True)
        method: str = serializer.validated_data.get('method')
        margin_budget: float = serializer.validated_data.get('margin_budget')
        max_horizon: int = serializer.validated_data.get('max_horizon')
        custom: dict = serializer.validated_data.get('custom')

        hedge_settings = CustomerAPIService().set_hedge_policy_for_account(
            account_id=pk,
            method=method,  # TODO: use HedgeMethod(Enum)
            margin_budget=margin_budget,
            max_horizon=max_horizon,
            custom_settings=custom,
        )
        serializer = HedgeSettingsSerializer(hedge_settings)
        return Response(serializer.data)

    @extend_schema(
        request=HedgePolicyForAccountViewSerializer,
        responses={
            status.HTTP_200_OK: HedgeSettingsSerializer,
            status.HTTP_404_NOT_FOUND: ActionStatusSerializer
        }
    )
    @action(detail=True, methods=['get'])
    def get_hedge_policy(self, request, pk: int):
        """
        Get an account's hedge policy.
        """

        _ = get_object_or_404(AccountViewSet.queryset, pk=pk)

        hedge_settings = CustomerAPIService().get_hedge_policy_for_account(account_id=pk)
        if hedge_settings is None:
            return get_response_from_action_status(
                http_status=status.HTTP_404_NOT_FOUND,
                action_status=ActionStatus(
                    message="Error: Account hedge settings not set",
                    status=ActionStatus.Status.ERROR,
                ),
            )
        serializer = HedgeSettingsSerializer(hedge_settings)
        return Response(serializer.data)
