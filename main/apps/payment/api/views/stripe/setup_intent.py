from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.account.models import Company
from main.apps.billing.services.stripe.payment import StripePaymentService
from main.apps.payment.api.serializers.stripe.setup_intent import StripeSetupIntentSerializer


class StripeSetupIntentView(APIView):
    def __init__(self):
        self.stripe = StripePaymentService()

    permission_classes = [IsAuthenticated, ]

    @extend_schema(
        responses={200: StripeSetupIntentSerializer}
    )
    def get(self, request):
        user = request.user
        if user.company.stripe_setup_intent_id is None:
            # Create intent if no intent id is set and return that intent
            intent = self.stripe.create_setup_intent_for_company(user.company)
        else:
            intent = self.stripe.retrieve_setup_intent(setup_intent_id=user.company.stripe_setup_intent_id)
        serializer = StripeSetupIntentSerializer({"client_secret": intent.client_secret})
        data = serializer.data
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: StripeSetupIntentSerializer}
    )
    def post(self, request):
        user = request.user
        intent = self.stripe.create_setup_intent_for_company(user.company)
        serializer = StripeSetupIntentSerializer({"client_secret": intent.client_secret})
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)
