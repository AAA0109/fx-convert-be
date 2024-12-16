from django.core.cache import cache
from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, permissions, generics
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.ibkr.models import FutureContract
from main.apps.ibkr.models.future_contract import FutureContractIntra
from main.apps.marketdata.api.serializers.future import LiquidHoursSerializer, TradingHoursSerializer, \
    FutureIntraSerializer
from main.apps.marketdata.models.future.future_liquid_hour import FutureLiquidHours
from main.apps.marketdata.models.future.future_trading_hour import FutureTradingHours

future_trading_calender_param = [
    OpenApiParameter(name="start_date", location=OpenApiParameter.QUERY, description="Start date in ISO8601 format",
                     type=OpenApiTypes.STR),
    OpenApiParameter(name="end_date", location=OpenApiParameter.QUERY, description="End date in ISO8601 format",
                     type=OpenApiTypes.STR),
    OpenApiParameter(name="symbol", location=OpenApiParameter.QUERY,
                     description="Future symbol e.g. ECN2023",
                     type=OpenApiTypes.STR, many=False),
]

future_intra_params = [
    OpenApiParameter(name="base", location=OpenApiParameter.QUERY, description="Base for future contract",
                     type=OpenApiTypes.STR),
]


class FutureApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]


class FutureFilterMixin:
    def add_filter_params(self, queryset: QuerySet) -> QuerySet:
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        future_symbol = self.request.query_params.get("symbol")

        cache_key = f'future_contract_{future_symbol}'
        future_contract = cache.get(cache_key)

        if future_symbol is not None:
            try:
                future_contract = FutureContract.objects.get(fut_symbol=future_symbol)
                cache.set(cache_key, future_contract, timeout=3600)  # Cache for 1 hour (3600 seconds)
            except FutureContract.DoesNotExist:
                future_contract = None

        if future_contract is not None:
            queryset = queryset.filter(future_contract=future_contract)
        if start_date is not None:
            queryset = queryset.filter(date__gte=start_date)
        if end_date is not None:
            queryset = queryset.filter(date__lte=end_date)

        return queryset


class FutureIntraApiView(FutureApiView):
    @extend_schema(
        parameters=future_intra_params,
        responses={
            status.HTTP_200_OK: FutureIntraSerializer(many=True)
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """ Retreive all contracts by base_currency (response) """

        base = request.query_params.get('base', None)
        if base is not None:
            future_contracts = FutureContract.objects.filter(base=base)
            future_contract_ids = [future_contract.id for future_contract in future_contracts]
            contracts = FutureContractIntra.objects.filter(future_contract_id__in=future_contract_ids)
        else:
            contracts = FutureContractIntra.objects.all()

        serializer = FutureIntraSerializer(contracts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FutureTradingHoursApiView(generics.ListAPIView, FutureFilterMixin):
    serializer_class = TradingHoursSerializer

    ordering_fields = ['date']
    ordering = ['-date']

    @extend_schema(
        parameters=future_trading_calender_param
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        queryset = self.get_model_for_queryset()
        queryset = self.add_filter_params(queryset)
        return queryset

    def get_model_for_queryset(self) -> QuerySet:
        return FutureTradingHours.objects.all()


class FutureLiquidHoursApiView(generics.ListAPIView, FutureFilterMixin):
    serializer_class = LiquidHoursSerializer

    ordering_fields = ['date']
    ordering = ['-date']

    @extend_schema(
        parameters=future_trading_calender_param
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        queryset = self.get_model_for_queryset()
        queryset = self.add_filter_params(queryset)
        return queryset

    def get_model_for_queryset(self) -> QuerySet:
        return FutureLiquidHours.objects.all()
