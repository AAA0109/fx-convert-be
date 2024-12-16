from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status, permissions


from typing import Optional, Dict

from main.apps.country.api.serializers.models.country import CountrySerializer
from main.apps.country.models import Country


# ==========================
# SGE Views
# ==========================

class CountryViewSet(APIView):
    queryset = Country.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class CountryListApiView(CountryViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request, *args, **kwargs):
        """ Get all currency definitions """
        queryset = Country.objects.all()
        serializer = CountrySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CountryCurrencyApiView(CountryViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, country_code: str) -> Optional[Country]:
        """ Retreive the currency (object) """
        try:
            return Country.objects.filter(code=country_code)
        except Country.DoesNotExist:
            return None

    def get(self, request: Request, country_code: str, *args, **kwargs):
        """ Retreive the currency (response) """
        queryset = self.get_object(
            country_code=country_code)
        if not queryset:
            return Response(
                {"res": f"{country_code} does not exist"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CountrySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CurrencyCountryApiView(CountryViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, mnemonic: str) -> QuerySet:
        return Country.objects.filter(currency_code__mnemonic=mnemonic, use_in_average=True)

    def get(self, request: Request, mnemonic: str, *args, **kwargs):
        """ Retreive the currency (response) """
        queryset = self.get_object(mnemonic=mnemonic)
        if not queryset.exists():  # Use queryset.exists() to check if the queryset is empty
            return Response(
                {"res": f"{mnemonic} does not exist"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CountrySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
