from datetime import datetime
from typing import Optional
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status, permissions

from rest_framework.views import APIView
from main.apps.ibkr.api.serializers.future_contract import FutureContractSerializer
from main.apps.ibkr.models import FutureContract


class FutureContractApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]


class FutureContractDetailBySymbolApiView(FutureContractApiView):

    def get_object(self, symbol: str) -> Optional[FutureContract]:
        """ Retreive the contract (object) """
        try:
            return FutureContract.objects.get(fut_symbol=symbol)
        except FutureContract.DoesNotExist:
            return None

    @extend_schema(
        responses={
            status.HTTP_200_OK: FutureContractSerializer()
        }
    )
    def get(self, request: Request, symbol: str, *args, **kwargs):
        """ Retreive the contract (response) """

        contract = self.get_object(symbol=symbol)

        if not contract:
            return Response(
                {"res": f"Contract Object with symbol {symbol} does not exist"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = FutureContractSerializer(contract)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FutureContractByBaseApiView(FutureContractApiView):

    @extend_schema(
        responses={
            status.HTTP_200_OK: FutureContractSerializer(many=True)
        }
    )
    def get(self, request: Request, base: str, *args, **kwargs):
        """ Retreive all contracts by base_currency (response) """

        contracts = FutureContract.objects.filter(fut_base=base)

        serializer = FutureContractSerializer(contracts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FutureContractActiveByBaseApiView(FutureContractApiView):

    @extend_schema(
        responses={
            status.HTTP_200_OK: FutureContractSerializer(many=True)
        }
    )
    def get(self, request: Request, base: str, *args, **kwargs):
        """ Retreive all contracts by base_currency (response) """

        today = datetime.now().date()
        contracts = FutureContract.objects.filter(
            fut_base=base, fut_start_dt__lte=today, last_dt__gte=today)

        serializer = FutureContractSerializer(contracts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FutureContractActiveListApiView(FutureContractApiView):

    @extend_schema(
        responses={
            status.HTTP_200_OK: FutureContractSerializer(many=True)
        }
    )
    def get(self, request: Request, *args, **kwargs):
        """ Retreive all contracts by base_currency (response) """

        today = datetime.now().date()
        contracts = FutureContract.objects.filter(
            fut_start_dt__lte=today, last_dt__gte=today)

        serializer = FutureContractSerializer(contracts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
