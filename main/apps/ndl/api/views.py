from django.db.models import QuerySet, Avg
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status, permissions
from collections import defaultdict, OrderedDict
from datetime import datetime

from typing import Optional, Dict

from main.apps.ndl.api.serializers.models.sge import SGESerializer
from main.apps.ndl.models import sge
from main.apps.country.models import Country
# ==========================
# SGE Views
# ==========================


class SGEBaseView(APIView):
    queryset = sge.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class SGEListApiView(SGEBaseView):

    @extend_schema(
        summary="Get all currency definitions",
        responses={200: SGESerializer(many=True)}
    )
    def get(self, request: Request, *args, **kwargs):
        queryset = sge.objects.all()
        serializer = SGESerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SGEDetailApiView(SGEBaseView):

    def get_queryset(self, currency_code: str, value_type: str) -> Optional[QuerySet]:
        """ Retrieve the queryset of the corresponding records """
        return sge.objects.filter(currency__mnemonic=currency_code, value_type=value_type)

    @extend_schema(
        summary="Retrieve specific currency records based on currency_code and value_type",
        responses={200: SGESerializer(many=True), 400: "Error Message"}
    )
    def get(self, request: Request, currency_code: str, value_type: str, *args, **kwargs):
        queryset = self.get_queryset(
            currency_code=currency_code, value_type=value_type)
        if not queryset.exists():
            error_message = {}
            if not sge.objects.filter(currency__mnemonic=currency_code).exists():
                error_message['currency_error'] = f"{currency_code} does not exist"
            if not sge.objects.filter(value_type=value_type).exists():
                error_message['value_type_error'] = f"{value_type} does not exist"
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)

        serializer = SGESerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PTenAverageView(SGEBaseView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, value_type, *args, **kwargs):
        try:
            p10_list = [country.currency_code for country in Country.objects.filter(
                use_in_explore=True)]

            average_data = self.calculate_and_sort_average(
                p10_list, value_type)
            return Response(average_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def calculate_and_sort_average(self, currency_codes, value_type):
        date_value_dict = defaultdict(list)

        for code in currency_codes:
            results = sge.objects.filter(
                currency__mnemonic=code, value_type=value_type).values('date', 'value')

            for result in results:
                date = result['date'].strftime('%Y-%m')
                value = result['value']
                date_value_dict[date].append(value)

        average_data = {}
        for date, values in date_value_dict.items():
            if values:
                average = sum(values) / len(values)

                average_data[date] = round(average, 2)

        formatted_average_data = sorted([
            {
                "date": date,
                "value_type": value_type,
                "value": average,
                "currency_id": "P10",
                "country_codes": "Multiple"
            }
            for date, average in average_data.items()
        ], key=lambda x: datetime.strptime(x['date'], '%Y-%m'))

        return formatted_average_data
