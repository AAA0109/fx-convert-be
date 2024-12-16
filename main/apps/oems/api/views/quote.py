from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.oems.api.serializers.quote import (
    CreateQuoteRequestSerializer, QuoteResponseSerializer, QuoteToTicketRequestSerializer, UpdateQuoteRequestSerializer)
from main.apps.oems.api.serializers.ticket import TicketSerializer
from main.apps.oems.models import Quote
from main.apps.oems.services.order_quote import OrderQuoteService
from main.apps.oems.services.quote_ticket import QuoteToTicketFactory


class QuoteViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasCompanyAssociated]
    queryset = Quote.objects.all()
    serializer_class = QuoteResponseSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    def get_queryset(self):
        return Quote.objects.filter(user=self.request.user)

    @extend_schema(
        request=CreateQuoteRequestSerializer,
        responses={
            status.HTTP_201_CREATED: QuoteResponseSerializer,
        }
    )
    def create(self, request):
        """
        Create order quote record
        """
        serializer = CreateQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from_currency = serializer.validated_data.get('from_currency')
        to_currency = serializer.validated_data.get('to_currency')

        quote = OrderQuoteService().create_quote(company=request.user.company,
                                                 currency_from_mnemonic=from_currency, currency_to_mnemonic=to_currency, user=request.user)

        serializer = QuoteResponseSerializer(quote)
        data = serializer.data
        return Response(data, status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            status.HTTP_200_OK: QuoteResponseSerializer,
        }
    )
    def retrieve(self, request, id: int):
        """
        Get order quote record by id
        """
        quote = get_object_or_404(self.get_queryset(), pk=int(id))
        serializer = QuoteResponseSerializer(quote)
        return Response(serializer.data)

    @extend_schema(
        request=UpdateQuoteRequestSerializer,
        responses={
            status.HTTP_200_OK: QuoteResponseSerializer,
        }
    )
    def update(self, request, id: int):
        """
        Update order quote record
        """

        serializer = UpdateQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from_currency = serializer.validated_data.get('from_currency')
        to_currency = serializer.validated_data.get('to_currency')
        order_id = serializer.validated_data.get('order_id')

        quote = OrderQuoteService().update_quote(quote_id=id, currency_from_mnemonic=from_currency,
                                                 currency_to_mnemonic=to_currency, order_id=order_id)

        serializer = QuoteResponseSerializer(quote)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            status.HTTP_204_NO_CONTENT: None,
        }
    )
    def destroy(self, request, id: int):
        """
        Remove order quote record
        """
        Quote.objects.filter(pk=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuoteToTicketAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=QuoteToTicketRequestSerializer,
        responses={
            status.HTTP_200_OK: TicketSerializer,
        }
    )
    def post(self, request):
        serializer = QuoteToTicketRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            quote_to_ticket_factory = QuoteToTicketFactory()
            ticket = quote_to_ticket_factory.quote_to_ticket(**serializer.data)

            ticket = TicketSerializer(ticket)
            return Response(ticket.data, status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "msg": f"{e}"
            }, status.HTTP_400_BAD_REQUEST)

