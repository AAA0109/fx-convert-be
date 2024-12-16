from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from main.apps.core.utils.api import BrokerAccountBelongsToUser
from main.apps.currency.models import Currency
from main.apps.ibkr.api.serializers.fb import DepositRequestSerializer, IBFBResponseSerializer, \
    GetInstructionNameRequestSerializer, GetStatusSerializer, FundingRequestSerializer, WireInstructionSerializer, \
    ListWireInstructionsSerializers, PredefinedDestinationInstructionRequest, \
    WithdrawRequestSerializer, ListFundingRequestsSerializer
from main.apps.ibkr.models import FundingRequest, WireInstruction
from main.apps.ibkr.services.fb.fb import IBFBService


class IBFBViewMixin:
    permission_classes = (IsAuthenticated,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ib_fund_service = IBFBService()


class CreateDepositFundsView(IBFBViewMixin, generics.CreateAPIView):
    serializer_class = DepositRequestSerializer

    @extend_schema(
        request=DepositRequestSerializer,
        responses={
            status.HTTP_200_OK: IBFBResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        funding_request = self.ib_fund_service.deposit_funds(
            serializer.validated_data
        )
        response_serializer = IBFBResponseSerializer({
            'funding_request': funding_request
        })
        return Response(response_serializer.data, status.HTTP_200_OK)


class CreateWithdrawFundsView(IBFBViewMixin, generics.CreateAPIView):
    serializer_class = DepositRequestSerializer

    @extend_schema(
        request=WithdrawRequestSerializer,
        responses={
            status.HTTP_200_OK: IBFBResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        funding_request = self.ib_fund_service.withdraw_funds(
            serializer.validated_data
        )
        response_serializer = IBFBResponseSerializer({
            'funding_request': funding_request
        })
        return Response(response_serializer.data, status.HTTP_200_OK)


class GetInstructionNameView(IBFBViewMixin, generics.RetrieveAPIView):
    serializer_class = GetInstructionNameRequestSerializer

    @extend_schema(
        parameters=[GetInstructionNameRequestSerializer],
        responses={
            status.HTTP_200_OK: IBFBResponseSerializer
        }
    )
    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        broker_account_id = request.query_params.get('broker_account_id')
        funding_request = self.ib_fund_service.get_instruction_name(broker_account_id, serializer.validated_data)
        response_serializer = IBFBResponseSerializer({
            'funding_request': funding_request
        })
        return Response(response_serializer.data, status.HTTP_200_OK)


class GetStatusView(IBFBViewMixin, generics.RetrieveAPIView):
    """
    Service is used to poll for status using the previously uploaded fund request.
    """
    serializer_class = GetStatusSerializer

    @extend_schema(
        parameters=[GetStatusSerializer],
        responses={
            status.HTTP_200_OK: IBFBResponseSerializer
        }
    )
    def get(self, request: Request, *args, **kwargs):
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        funding_request = self.ib_fund_service.get_status(request.query_params.get('funding_request_id'))
        response_serializer = IBFBResponseSerializer({
            'funding_request': funding_request
        })
        return Response(response_serializer.data, status.HTTP_200_OK)


class ListFundingRequestsView(IBFBViewMixin, generics.ListAPIView):
    permission_classes = (IsAuthenticated, BrokerAccountBelongsToUser)
    serializer_class = FundingRequestSerializer

    def get_queryset(self):
        qs = FundingRequest.objects.all()
        broker_account_id = self.request.query_params.get('broker_account_id')
        qs.filter(broker_account_id=broker_account_id)
        method = self.request.query_params.get('method')
        if method is not None:
            qs.filter(method=method)
        return qs

    @extend_schema(
        parameters=[ListFundingRequestsSerializer],
        responses={
            status.HTTP_200_OK: FundingRequestSerializer(many=True)
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ListWireInstructionsView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = WireInstructionSerializer

    def get_queryset(self):
        qs = WireInstruction.objects.all()
        mnemonic = self.request.query_params.get('mnemonic')
        currency = Currency.get_currency(mnemonic)
        qs.filter(currency=currency)
        return qs

    @extend_schema(
        parameters=[ListWireInstructionsSerializers],
        responses={
            status.HTTP_200_OK: WireInstructionSerializer(many=True)
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CreatePredefinedDestinationInstructionView(IBFBViewMixin, generics.CreateAPIView):
    serializer_class = PredefinedDestinationInstructionRequest

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        funding_request = self.ib_fund_service.predefined_destination_instruction(serializer.validated_data)
        response_serializer = FundingRequestSerializer(funding_request)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=PredefinedDestinationInstructionRequest,
        responses={
            status.HTTP_200_OK: FundingRequestSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
