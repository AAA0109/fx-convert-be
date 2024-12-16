from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from main.apps.billing.services.stripe.payment import StripePaymentService
from main.apps.payment.api.serializers.stripe.payment_method import (
    StripePaymentMethodRequestSerializer,
    StripePaymentMethodResponseSerializer
)

class StripePaymentMethodView(APIView):
    def __init__(self):
        self.stripe = StripePaymentService()

    permission_classes = [IsAuthenticated, ]

    @extend_schema(
        request=StripePaymentMethodRequestSerializer,
        responses={200: StripePaymentMethodResponseSerializer}
    )
    def post(self, request):
        payment_method_id = request.data['payment_method_id']
        payment_method = self.stripe.retrieve_payment_method(payment_method_id=payment_method_id)
        data = self._get_payment_method_data(payment_method)
        serializer = StripePaymentMethodResponseSerializer(data)
        data = serializer.data
        return Response(data, status=status.HTTP_200_OK)

    def _get_payment_method_data(self, payment_method):
        data = {
            "id": payment_method.id,
            "type": payment_method.type
        }

        if payment_method.type == 'card':
            data['last4'] = payment_method.card.last4
            data['brand'] = payment_method.card.brand

        if payment_method.type == 'us_bank_account':
            data['last4'] = payment_method.us_bank_account.last4
            data['brand'] = payment_method.us_bank_account.bank_name

        return data
