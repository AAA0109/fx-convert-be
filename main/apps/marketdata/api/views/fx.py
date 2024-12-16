from datetime import timedelta, datetime

from django.core.cache import cache
from django.db.models import QuerySet, Avg
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from hdlib.DateTime.Date import Date
import pytz

from rest_framework import generics, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.country.models import Country
from main.apps.currency.api.serializers.models.currency import FxPairSerializer
from main.apps.currency.models import FxPair

from main.apps.marketdata.models import DataCut, TradingCalendar, FxSpotVol
from main.apps.marketdata.models.fx.rate import (
    FxForward,
    FxSpot, FxSpotIntra
)
from main.apps.marketdata.api.serializers.fx.forward import FxForwardSerializer
from main.apps.marketdata.api.serializers.fx.spot import (
    AverageFxSpotPriceRequestSerializer, AverageFxSpotPriceSerializer, FxSpotSerializer, FxSpotIntraSerializer,
    FxSpotVolSerializer
)
from main.apps.marketdata.api.serializers.fx.trading_calendar import TradingCalendarSerializer

fx_intra_params = [
    OpenApiParameter(name="start_date", location=OpenApiParameter.QUERY, description="Start date in ISO8601 format",
                     type=OpenApiTypes.STR),
    OpenApiParameter(name="end_date", location=OpenApiParameter.QUERY, description="End date in ISO8601 format",
                     type=OpenApiTypes.STR),
    OpenApiParameter(name="pair_ids", location=OpenApiParameter.QUERY,
                     description="Comma separated list of FX Pair IDs",
                     type=OpenApiTypes.INT, many=True),
]

fx_params = fx_intra_params.copy()
fx_params.append(
    OpenApiParameter(name="data_cut_type", location=OpenApiParameter.QUERY,
                     description="Data cut type: (eod, intra, benchmark)",
                     type=OpenApiTypes.STR)
)


# ==========================
# FxSpot Views
# ==========================
class FxApiView(generics.ListAPIView):
    ordering_fields = ['date']
    ordering = ['-date']

    @extend_schema(
        parameters=fx_params
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        queryset = self.get_model_for_queryset()
        queryset = self.add_filter_params(queryset)
        return queryset

    def get_model_for_queryset(self) -> QuerySet:
        raise NotImplementedError

    def add_filter_params(self, queryset: QuerySet) -> QuerySet:
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        pair_ids = self.request.query_params.get("pair_ids")
        data_cut_type = self.request.query_params.get("data_cut_type")
        if pair_ids is not None:
            queryset = queryset.filter(pair_id__in=pair_ids.split(','))
        if start_date is not None:
            if self.__class__ == FxSpotIntraApiView:
                queryset = queryset.filter(date__gte=start_date)
            else:
                queryset = queryset.filter(data_cut__cut_time__gte=start_date)
        if end_date is not None:
            if self.__class__ == FxSpotIntraApiView:
                queryset = queryset.filter(date__lte=end_date)
            else:
                queryset = queryset.filter(data_cut__cut_time__lte=end_date)
        if data_cut_type is not None:
            _data_cut_type = None
            if data_cut_type == 'eod':
                _data_cut_type = DataCut.CutType.EOD
            if data_cut_type == 'intra':
                _data_cut_type = DataCut.CutType.INTRA
            if data_cut_type == 'benchmark':
                _data_cut_type = DataCut.CutType.BENCHMARK
            if _data_cut_type:
                queryset = queryset.filter(data_cut__cut_type=_data_cut_type)

        return queryset


class FxSpotApiView(FxApiView):
    serializer_class = FxSpotSerializer

    def get_model_for_queryset(self) -> QuerySet:
        return FxSpot.objects.select_related('pair__base_currency', 'pair__quote_currency').all()


class FxSpotVolApiView(FxApiView):
    serializer_class = FxSpotVolSerializer

    def get_model_for_queryset(self) -> QuerySet:
        return FxSpotVol.objects.select_related('pair__base_currency', 'pair__quote_currency').all()


class P10FxPairView(generics.ListAPIView):
    serializer_class = FxPairSerializer

    def get_queryset(self) -> QuerySet:
        cache_key = 'p10_currency_codes'
        p10_list = cache.get(cache_key)

        if p10_list is None:
            p10_list = list(Country.objects.filter(use_in_explore=True).values_list('currency_code', flat=True))
            cache.set(cache_key, p10_list, timeout=3600)  # Cache for 1 hour (3600 seconds)

        return FxPair.objects.filter(quote_currency__mnemonic__in=p10_list)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Create a list of pair_ids based on the queryset
        pair_ids = [item['id'] for item in data]

        # Define date range for six months from today
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)

        # Adjust start_date to the first day of the month
        start_date = start_date.replace(day=1)

        # Filter objects within date range and pair_id, and calculate averages for each date
        queryset = FxSpotVol.objects.filter(
            pair_id__in=pair_ids,
            date__range=[start_date, end_date]
        ).annotate(month=TruncDate('date')).values('month').annotate(avg_vol=Avg('vol')).order_by('month')

        # Convert queryset to list
        daily_averages = list(queryset)

        return JsonResponse({'p10_monthly_averages': daily_averages})


class FxSpotIntraApiView(FxSpotApiView):
    serializer_class = FxSpotIntraSerializer

    @extend_schema(
        parameters=fx_intra_params
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_model_for_queryset(self) -> QuerySet:
        return FxSpotIntra.objects.select_related('pair__base_currency', 'pair__quote_currency').all()


# ==========================
# FxForward Views
# ==========================
fx_forward_params = fx_params.copy()
fx_forward_params.append(
    OpenApiParameter(name="tenor", location=OpenApiParameter.QUERY, description="Comma seperated list of tenors",
                     type=OpenApiTypes.INT, many=True))


class FxForwardApiView(FxApiView):
    serializer_class = FxForwardSerializer

    @extend_schema(
        parameters=fx_forward_params
    )
    def get(self, request: Request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_model_for_queryset(self) -> QuerySet:
        return FxForward.objects.all()

    def add_filter_params(self, queryset: QuerySet) -> QuerySet:
        queryset = super().add_filter_params(queryset)
        tenor = self.request.query_params.get("tenor")
        if tenor is not None:
            queryset = queryset.filter(tenor__in=tenor.split(","))
        return queryset


# ==========================
# Trading Calendar Views
# ==========================
class TradingCalendarApiView(FxApiView):
    serializer_class = TradingCalendarSerializer

    def get_model_for_queryset(self) -> QuerySet:
        return TradingCalendar.objects.all()

    def add_filter_params(self, queryset: QuerySet) -> QuerySet:
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        pair_ids = self.request.query_params.get("pair_ids")
        if pair_ids is not None:
            queryset = queryset.filter(pair_id__in=pair_ids.split(','))
        if start_date is not None:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date is not None:
            queryset = queryset.filter(end_date__gte=end_date)

        return queryset


# ==========================
# Average Fx Spot Intra Views
# ==========================
class FxSpotIntraAverageApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[AverageFxSpotPriceRequestSerializer],
        responses={
            status.HTTP_200_OK: AverageFxSpotPriceSerializer()
        }
    )
    def get(self, request, *args, **kwargs):
        """ Retreive the fx spot intra average over the last hour (response) """
        serializer = AverageFxSpotPriceRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        pair_id = serializer.validated_data.get('pair_id')

        tz = pytz.timezone('US/Eastern')
        now = Date.now().astimezone(tz=tz)
        last_hour = now - timedelta(hours=1)
        pair = FxPair.get_pair(pair_id)

        if not pair:
            return Response(
                {"res": f"Currency pair for pair id {pair_id} doesn't exist"},
                status=status.HTTP_400_BAD_REQUEST
            )

        spot_data_last_hour = FxSpotIntra.objects.filter(date__gte=last_hour, date__lte=now, pair=pair).aggregate(
            average_rate=Avg('rate'), average_rate_bid=Avg('rate_bid'), average_rate_ask=Avg('rate_ask'))

        average_fx_spot_obj = {
            "pair": pair,
            "average_rate": spot_data_last_hour['average_rate'] or 0,
            "average_rate_bid": spot_data_last_hour['average_rate_bid'] or 0,
            "average_rate_ask": spot_data_last_hour['average_rate_ask'] or 0,
        }

        serializer = AverageFxSpotPriceSerializer(average_fx_spot_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)
