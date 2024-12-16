from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status, permissions, viewsets

from main.apps.currency.models.currency import Currency
from main.apps.currency.api.serializers.models.currency import (
    CurrencyDeliverySerializer,
    CurrencySerializer,
    FxPairSerializer,
    StabilityIndexSerializer
)
from main.apps.currency.models.deliverytime import DeliveryTime
from main.apps.currency.models.fxpair import FxPair
from main.apps.currency.models.stabilityIndex import StabilityIndex
from typing import Optional, Dict

from main.apps.marketdata.models import FxSpot
from main.apps.util import get_or_none


# ==========================
# Currency Views
# ==========================
class CurrencyApiView(APIView):
    queryset = Currency.objects.all()
    permission_classes = [permissions.AllowAny]


class CurrencyListApiView(CurrencyApiView):
    @extend_schema(
        responses={
            status.HTTP_200_OK: CurrencySerializer(many=True)
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """ Get all currency definitions """
        currencies = Currency.objects.all()
        serializer = CurrencySerializer(currencies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CurrencyDetailApiView(CurrencyApiView):

    def get_object(self, mnemonic: str) -> Optional[Currency]:
        """ Retreive the currency (object) """
        try:
            return Currency.objects.get(mnemonic=mnemonic)
        except Currency.DoesNotExist:
            return None

    @extend_schema(
        responses={
            status.HTTP_200_OK: CurrencySerializer
        }
    )
    def get(self, request: Request, mnemonic: str, *args, **kwargs):
        """ Retreive the currency (response) """
        currency = self.get_object(mnemonic=mnemonic)
        if not currency:
            return Response(
                {"res": f"Currency Object with mnemonic {mnemonic} does not exist"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CurrencySerializer(currency)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# FX Pair Views
# ==========================


class FxPairViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FxPairSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return FxPair.get_pairs()


# ==========================
# Stability Index Views
# ==========================


class StabilityIndexApiView(APIView):
    queryset = StabilityIndex.objects.all()
    serializer_class = StabilityIndexSerializer
    permission_classes = [permissions.AllowAny]


class StabilityIndexListApiView(StabilityIndexApiView):
    @extend_schema(
        responses={
            status.HTTP_200_OK: StabilityIndexSerializer(many=True)
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """ Get all stability index definitions """
        stabilityIndex = StabilityIndex.objects.all()
        serializer = StabilityIndexSerializer(stabilityIndex, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StabilityIndexDetailApiView(StabilityIndexApiView):
    @extend_schema(
        responses={
            status.HTTP_200_OK: StabilityIndexSerializer(many=True)
        }
    )

    def get_currency(self, mnemonic: str) -> Optional[Currency]:
        """ Retrieve the currency object """
        try:
            return Currency.objects.get(mnemonic=mnemonic)
        except Currency.DoesNotExist:
            return None

    def get_stability_indexes(self, currency: Currency, year: int) -> Optional[StabilityIndex]:
        """ Retrieve stability indexes for a specific currency """
        stability_indexes = StabilityIndex.objects.filter(currency=currency, date__year=year)
        return stability_indexes

    def get(self, request: Request, *args, **kwargs):
        """ Retrieve stability indexes for a specific currency """
        currency_mnemonic = kwargs.get('mnemonic')
        year = kwargs.get('year')
        currency = self.get_currency(mnemonic=currency_mnemonic)

        if not currency:
            return Response(
                {"res": f"Currency Object with mnemonic {currency_mnemonic} does not exist"},
                status=status.HTTP_400_BAD_REQUEST
            )

        stability_indexes = self.get_stability_indexes(currency=currency, year=year)
        serializer = StabilityIndexSerializer(stability_indexes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


#==========================
# Currency Delivery Time
#=========================


class DeliveryTimeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeliveryTime.objects.all()
    serializer_class = CurrencyDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]


class CurrencyDeliveryTimeApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @get_or_none
    def get_object(self, currency: Currency) -> Optional[DeliveryTime]:
        return DeliveryTime.objects.get(currency=currency)

    @extend_schema(
        responses={
            status.HTTP_200_OK: CurrencyDeliverySerializer()
        }
    )
    def get(self, request: Request, mnemonic: str, *args, **kwargs):
        """ Retreive the currency delivery time (response) """
        currency = Currency.objects.get(mnemonic=mnemonic)
        delivery_time = self.get_object(currency=currency)
        if not delivery_time:
            return Response(
                {"message": f"Delivery time for {mnemonic} does not exist"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CurrencyDeliverySerializer(delivery_time)
        return Response(serializer.data, status=status.HTTP_200_OK)
