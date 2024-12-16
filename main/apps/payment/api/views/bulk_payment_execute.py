import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.payment.api.serializers.payment import FailedPaymentRfqSerializer
from main.apps.payment.api.serializers.bulk_payment import (
    BulkExecutionStatusSerializer,
    BulkPaymentExecutionSerializer
)
from main.apps.payment.api.serializers.payment_execution import PaymentExecutionResponseSerializer
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.batch_response import BatchResponseProvider
from main.apps.payment.services.error_utils import PaymentResponseUtils
from main.apps.payment.services.payment_execution import BulkPaymentExecutionService

logger = logging.getLogger(__name__)


class BulkPaymentExecutionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    def get_queryset(self):
        return Payment.objects.filter(cashflow_generator__company=self.request.user.company)

    @extend_schema(
        request=BulkPaymentExecutionSerializer,
        responses={
            status.HTTP_200_OK: BulkExecutionStatusSerializer
        }
    )
    def post(self, request):
        try:
            serializer = BulkPaymentExecutionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            bulk_execution_service = BulkPaymentExecutionService()
            execution_status = bulk_execution_service.bulk_payment_execution(
                request=request,
                payment_ids=serializer.validated_data.get('payment_ids')
            )
            resp = BulkExecutionStatusSerializer({'executions':execution_status})
            return BatchResponseProvider().generate_response(serialized_response=resp.data)
        except serializers.ValidationError as e:
            error_resp = PaymentResponseUtils().create_validation_error_response(e=e)
            return Response(error_resp, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
