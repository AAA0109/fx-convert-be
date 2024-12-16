import logging
from django.http import Http404

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.payment.api.serializers.payment import DetailedPaymentRfqResponseSerializer
from main.apps.payment.api.serializers.payment_execution import PaymentExecutionResponseSerializer
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.payment_execution import PaymentExecutionService
from main.apps.payment.services.payment_rfq import PaymentRfqService
from main.apps.payment.services.rfq_error import RfqErrorProvider

logger = logging.getLogger(__name__)


class PaymentRfqAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    def get_queryset(self):
        return Payment.objects.filter(cashflow_generator__company=self.request.user.company)

    @extend_schema(
        responses={
            status.HTTP_200_OK: DetailedPaymentRfqResponseSerializer
        }
    )
    def get(self, request, pk: int):
        try:
            payment = get_object_or_404(self.get_queryset(), pk=pk)
            rfq_service = PaymentRfqService(payment=payment)
            rfq_status = rfq_service.create_ticket(request=request)
            serializer = DetailedPaymentRfqResponseSerializer(rfq_status)
            status_code = RfqErrorProvider().get_status_code(serialized_response=serializer.data)
            return Response(serializer.data, status=status_code)
        except Http404 as e:
            error_response = RfqErrorProvider().generate_response(exception=e)
            return Response(error_response, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(e, exc_info=True)
            error_response = RfqErrorProvider().generate_response(exception=e)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentExecutionAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    def get_queryset(self):
        return Payment.objects.filter(cashflow_generator__company=self.request.user.company)

    @extend_schema(
        responses={
            status.HTTP_200_OK: PaymentExecutionResponseSerializer
        }
    )
    def get(self, request, pk: int):
        try:
            payment = get_object_or_404(self.get_queryset(), pk=pk)
            execution_service = PaymentExecutionService(payment=payment, request=request)
            response = execution_service.execute()
            serializer = PaymentExecutionResponseSerializer(response)
            status_code = RfqErrorProvider().get_status_code(serialized_response=serializer.data)
            return Response(serializer.data, status=status_code)
        except Http404 as e:
            error_response = RfqErrorProvider().generate_response(exception=e)
            return Response(error_response, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(e, exc_info=True)
            error_response = RfqErrorProvider().generate_response(exception=e)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
