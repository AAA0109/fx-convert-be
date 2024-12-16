from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated

from main.apps.marketdata.api.filters.fx import get_spot_filter_for_model, get_forward_filter_for_model
from main.apps.marketdata.api.serializers.corpay.fxspot import CorPayFxSpotSerializer, CorPayFxForwardSerializer
from main.apps.marketdata.models import CorpayFxSpot, CorpayFxForward


class FxSpotCorpayApiViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CorPayFxSpotSerializer
    queryset = CorpayFxSpot.objects.all()
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = get_spot_filter_for_model(CorpayFxSpot)
    ordering_fields = ['date']
    ordering = ['-date']


class FxForwardCorpayApiViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CorPayFxForwardSerializer
    queryset = CorpayFxForward.objects.all()
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = get_forward_filter_for_model(CorpayFxForward)
    ordering_fields = ['date']
    ordering = ['-date']
