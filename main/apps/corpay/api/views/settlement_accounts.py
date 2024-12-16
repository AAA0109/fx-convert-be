from drf_spectacular.utils import extend_schema
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from main.apps.corpay.api.serializers.settlement_accounts.settlement_account import \
    SettlementAccountsResponseSerializer, FXBalanceAccountsResponseSerializer, FXBalanceAccountsRequestSerializer, \
    FXBalanceHistoryRequestSerializer, \
    CompanyFXBalanceAccountHistorySerializer, FXBalanceAccountHistoryRowSerializer
from main.apps.corpay.api.views.base import CorPayBaseView
from main.apps.corpay.models import FXBalance, CorpaySettings
from main.apps.corpay.services.api.dataclasses.settlement_accounts import ViewFXBalanceAccountsParams


class ListSettlementAccountsView(CorPayBaseView):
    @extend_schema(
        responses={
            status.HTTP_200_OK: SettlementAccountsResponseSerializer
        }
    )
    def get(self, request):
        self.corpay_service.init_company(request.user.company)
        response = self.corpay_service.list_settlement_accounts()
        response_serializer = SettlementAccountsResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class ListFXBalanceAccountsView(CorPayBaseView):
    @extend_schema(
        parameters=[FXBalanceAccountsRequestSerializer],
        responses={
            status.HTTP_200_OK: FXBalanceAccountsResponseSerializer
        }
    )
    def get(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = FXBalanceAccountsRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        params = ViewFXBalanceAccountsParams(
            includeBalance=serializer.validated_data.get('include_balance')
        )
        response = self.corpay_service.list_fx_balance_accounts(data=params)
        try:
            settings = CorpaySettings.objects.get(company=request.user.company)
            if settings.fee_wallet_id is not None:
                response['data']['rows'] = [
                    row for row in response['data']['rows']
                    if row['accountNumber'] != settings.fee_wallet_id
                ]
                response['items'] = [
                    item for item in response['items']
                    if item['text'] != settings.fee_wallet_id
                ]
        except Exception as e:
            ...
        response_serializer = FXBalanceAccountsResponseSerializer(response, context={'company': request.user.company})
        return Response(response_serializer.data, status.HTTP_200_OK)


@extend_schema(
        parameters=[FXBalanceHistoryRequestSerializer],
        responses={
            status.HTTP_200_OK: FXBalanceAccountHistoryRowSerializer
        }
    )
class ListFXBalanceHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FXBalanceAccountHistoryRowSerializer
    queryset = FXBalance.objects.all()

    def get_serializer_context(self):
        req_serializer = FXBalanceHistoryRequestSerializer(data=self.request.GET)
        req_serializer.is_valid(raise_exception=True)
        return req_serializer

    def filter_queryset(self, queryset):
        req_serializer = self.get_serializer_context()

        queryset = super().filter_queryset(queryset)
        queryset = queryset.filter(
            company=self.request.user.company,
            account_number=req_serializer.validated_data.get('fx_balance_id')
        ).order_by(req_serializer.validated_data['ordering'])

        if val := req_serializer.validated_data.get('from_date'):
            queryset = queryset.filter(date__gte=val)

        if val := req_serializer.validated_data.get('to_date'):
            queryset = queryset.filter(date__lte=val)

        if req_serializer.validated_data.get('include_details'):
            queryset = queryset.prefetch_related('details')

        return queryset


class ListCompanyFXBalanceHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CompanyFXBalanceAccountHistorySerializer
    queryset = FXBalance.objects.all().prefetch_related('currency', 'details', 'details__currency')

    def filter_queryset(self, queryset):
        company = self.request.user.company
        return queryset.filter(company=company)
