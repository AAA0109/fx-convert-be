import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.payment.api.serializers.bulk_payment import (
    BulkPaymentRfqSerializer,
    BulkRfqStatusSerializer
)
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.batch_response import BatchResponseProvider
from main.apps.payment.services.error_utils import PaymentResponseUtils
from main.apps.payment.services.payment_rfq import BulkPaymentRfqService

logger = logging.getLogger(__name__)


class BulkPaymentRfqAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    def get_queryset(self):
        return Payment.objects.filter(cashflow_generator__company=self.request.user.company)

    @extend_schema(
        request=BulkPaymentRfqSerializer,
        responses={
            status.HTTP_200_OK: BulkRfqStatusSerializer
        }
    )
    def post(self, request):
        serializer = BulkPaymentRfqSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            bulk_rfq_service = BulkPaymentRfqService()
            bulk_rfq_status = bulk_rfq_service.bulk_payment_rfq(
                request=request,
                payment_ids=serializer.validated_data.get('payment_ids')
            )
            resp = BulkRfqStatusSerializer({'rfqs':bulk_rfq_status})
            return BatchResponseProvider().generate_response(serialized_response=resp.data)
        except serializers.ValidationError as e:
            error_resp = PaymentResponseUtils().create_validation_error_response(e=e)
            return Response(error_resp, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
