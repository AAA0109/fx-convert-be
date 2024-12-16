from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from main.apps.corpay.api.serializers.mass_payments import QuotePaymentsResponseSerializer, \
    QuotePaymentsRequestSerializer, BookPaymentsRequestSerializer, \
    BookPaymentsResponseSerializer
from main.apps.corpay.api.views.base import CorPayBaseView
from main.apps.corpay.services.api.dataclasses.mass_payment import BookPaymentsParams, \
    BookPaymentsBody


class CorPayQuotePaymentsView(CorPayBaseView):
    @extend_schema(
        request=QuotePaymentsRequestSerializer,
        responses={
            status.HTTP_200_OK: QuotePaymentsResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        self.corpay_service.init_company(request.user.company)
        serializer = QuotePaymentsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self.corpay_service.quote_payments(data=serializer.validated_data)
        response_serializer = QuotePaymentsResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class CorPayBookPaymentsView(CorPayBaseView):
    @extend_schema(
        request=BookPaymentsRequestSerializer,
        responses={
            status.HTTP_200_OK: BookPaymentsResponseSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        self.corpay_service.init_company(request.user.company)
        serializer = BookPaymentsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = BookPaymentsParams(
            quoteKey=serializer.validated_data.get('quote_id'),
            loginSessionId=serializer.validated_data.get('session_id')
        )
        data = BookPaymentsBody(
            combineSettlements=serializer.validated_data.get('combine_settlements')
        )
        response = self.corpay_service.book_payments(
            params=params,
            data=data
        )
        response_serializer = BookPaymentsResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)
