from typing import List
from rest_framework import viewsets
from rest_framework import views, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny

from main.apps.corpay.api.serializers.fxpairs import SupportedFxPairsSerializer
from main.apps.corpay.models import SupportedFxPairs
from main.apps.corpay.models.currency import CurrencyDefinition
from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair


class SupportedPairViewset(viewsets.ModelViewSet):
    queryset = SupportedFxPairs.objects.all()
    serializer_class = SupportedFxPairsSerializer
    http_method_names = ['get']
