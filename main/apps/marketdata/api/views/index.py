from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from main.apps.marketdata.api.serializers.index.index import IndexSerializer

from main.apps.marketdata.models import Index, IndexAsset

index_params = [
    OpenApiParameter(name="start_date", location=OpenApiParameter.QUERY, description="Start date in ISO8601 format",
                     type=OpenApiTypes.STR),
    OpenApiParameter(name="end_date", location=OpenApiParameter.QUERY, description="End date in ISO8601 format",
                     type=OpenApiTypes.STR),
    OpenApiParameter(name="symbol", location=OpenApiParameter.QUERY,
                     description="Index asset symbol",
                     type=OpenApiTypes.STR),
]


class IndexBaseApiView(generics.ListAPIView):
    ordering_fields = ['date']
    ordering = ['-date']

    @extend_schema(
        parameters=index_params
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
        symbol = self.request.query_params.get("symbol")
        if symbol is not None:
            index_asset = IndexAsset.objects.filter(symbol=symbol).first()
            queryset = queryset.filter(index_asset=index_asset)
        if start_date is not None:
            queryset = queryset.filter(date__gte=start_date)
        if end_date is not None:
            queryset = queryset.filter(date__lte=end_date)

        return queryset


class IndexApiView(IndexBaseApiView):
    serializer_class = IndexSerializer

    @extend_schema(
        parameters=index_params
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_model_for_queryset(self) -> QuerySet:
        return Index.objects.all()
