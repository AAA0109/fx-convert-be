import logging
from rest_framework import status, viewsets
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.payment.api.serializers.bulk_payment import (
    BulkPaymentRequestSerializer,
    BulkPaymentResponseSerializer,
    BulkPaymentUpdateSerializer,
    BulkPaymentValidationErrorResponseSerializer
)
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.error_utils import PaymentResponseUtils
from main.apps.payment.services.payment import BulkPaymentService
from main.apps.payment.services.validation import BulkPaymentValidationResponseProvider


class BulkPaymentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    def get_queryset(self):
        return Payment.objects.select_related('cashflow_generator').prefetch_related('cashflow_generator__cashflows')\
            .filter(cashflow_generator__company=self.request.user.company)

    @extend_schema(
        description="Create new company's bulk payment",
        request=BulkPaymentRequestSerializer,
        responses={
            status.HTTP_201_CREATED: BulkPaymentResponseSerializer
        }
    )
    def create(self, request):
        try:
            serializer = BulkPaymentRequestSerializer(data=request.data, context={'user': request.user})
            serializer.is_valid(raise_exception=True)

            bulk_payment_service = BulkPaymentService(company=request.user.company,
                                                      user=request.user,
                                                      validated_data=serializer.validated_data.get('payments'))
            payments, netting_result = bulk_payment_service.bulk_create_payments()

            resp_serializer = BulkPaymentResponseSerializer({'payments': payments, 'netting': netting_result})
            return Response(resp_serializer.data, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            error_resp = PaymentResponseUtils().create_validation_error_response(e=e)
            return Response(error_resp, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Update company's bulk payment",
        request=BulkPaymentUpdateSerializer,
        responses={
            status.HTTP_200_OK: BulkPaymentResponseSerializer
        }
    )
    def update(self, request):
        try:
            serializer = BulkPaymentUpdateSerializer(data=request.data, context={'user': request.user})
            serializer.is_valid(raise_exception=True)

            bulk_payment_service = BulkPaymentService(company=request.user.company,
                                                      user=request.user,
                                                      validated_data=serializer.validated_data,
                                                      is_update=True)
            payments, netting_result = bulk_payment_service.bulk_update_payments()
            resp_serializer = BulkPaymentResponseSerializer({'payments': payments, 'netting': netting_result})
            return Response(resp_serializer.data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            error_resp = PaymentResponseUtils().create_validation_error_response(e=e)
            return Response(error_resp, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BulkPaymentValidationViewSet(BulkPaymentViewSet):

    @extend_schema(
        description="Validate company's bulk payment data",
        request=BulkPaymentRequestSerializer,
        responses={
            status.HTTP_200_OK: BulkPaymentRequestSerializer,
            status.HTTP_400_BAD_REQUEST: BulkPaymentValidationErrorResponseSerializer
        }
    )
    def create(self, request):
        try:
            serializer = BulkPaymentRequestSerializer(data=request.data, context={'user': request.user})
            serializer.is_valid(raise_exception=True)
            return Response(request.data, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            error_resp = PaymentResponseUtils().create_validation_error_response(e=e)
            validation_results = BulkPaymentValidationResponseProvider().generate_validation_error_response(
                validation_errors=error_resp['validation_errors'])
            error_serializer = BulkPaymentValidationErrorResponseSerializer(data=validation_results)
            error_serializer.is_valid()
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
