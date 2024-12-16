import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from main.apps.corpay.api.serializers.forwrads.book_quote import ForwardBookQuoteRequestSerializer, \
    ForwardBookQuoteResponseSerializer
from main.apps.corpay.api.serializers.forwrads.complete_order import ForwardCompleteOrderRequestSerializer, \
    ForwardCompleteOrderResponseSerializer
from main.apps.corpay.api.serializers.forwrads.quote import ForwardQuoteResponseSerializer, \
    ForwardQuoteRequestSerializer
from main.apps.corpay.api.views.base import CorPayBaseView
from main.apps.corpay.services.api.dataclasses.forwards import CompleteOrderBody

logger = logging.getLogger(__name__)


class CreateForwardQuoteView(CorPayBaseView):

    @extend_schema(
        request=ForwardQuoteRequestSerializer,
        responses={
            status.HTTP_200_OK: ForwardQuoteResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = ForwardQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self.corpay_service.get_forward_quote(data=serializer.validated_data)
        response_serializer = ForwardQuoteResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class CreateForwardBookQuoteView(CorPayBaseView):

    @extend_schema(
        request=ForwardBookQuoteRequestSerializer,
        responses={
            status.HTTP_200_OK: ForwardBookQuoteResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = ForwardBookQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self.corpay_service.book_forward_quote(
            quote_id=serializer.validated_data.get('quote_id')
        )
        response_serializer = ForwardBookQuoteResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class CreateForwardCompleteOrderView(CorPayBaseView):
    @extend_schema(
        request=ForwardCompleteOrderRequestSerializer,
        responses={
            status.HTTP_200_OK: ForwardCompleteOrderResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = ForwardCompleteOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self.corpay_service.complete_order(
            forward_id=serializer.validated_data.get('forward_id'),
            data=CompleteOrderBody(
                settlementAccount=serializer.validated_data.get('settlement_account'),
                forwardReference=serializer.validated_data.get('forward_reference')
            )
        )
        response_serializer = ForwardCompleteOrderResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)
