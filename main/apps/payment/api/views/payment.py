import logging
import django_filters
from rest_framework import serializers as srz

from django.http.response import Http404
from django.core.exceptions import BadRequest
from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets, mixins
from rest_framework.views import APIView
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from main.apps.approval.services.payment_approval import PaymentApprovalService
from main.apps.cashflow.models.cashflow import SingleCashFlow

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.payment.api.serializers.payment import (
    InstallmentCashflowSerializer,
    PaymentErrorSerializer,
    PaymentSerializer,
    PaymentValidationErrorSerializer
)
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.cashflow import PaymentCashflowService
from main.apps.payment.services.error_utils import PaymentResponseUtils
from main.apps.payment.services.payment import PaymentService


logger = logging.getLogger(__name__)


class PaymentFilter(django_filters.FilterSet):
    class Meta:
        model = Payment
        fields = {
            'payment_status': ['exact']
        }


class PaymentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)
    filterset_class = PaymentFilter
    ordering = ['-cashflow_generator__value_date']
    ordering_fields = ['cashflow_generator__value_date']
    queryset = Payment.objects.select_related('cashflow_generator', 'cashflow_generator__cashflows').all()
    search_fields = ['id', 'cashflow_generator__name', 'cashflow_generator__amount']
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = Payment.objects.filter(
            cashflow_generator__company=self.request.user.company
        ).select_related(
            'auth_user',
            'create_user',
            'cashflow_generator',
            'cashflow_generator__buy_currency',
            'cashflow_generator__sell_currency',
            'cashflow_generator__lock_side',
            'cashflow_generator__company'
        ).prefetch_related(
            Prefetch(
                'cashflow_generator__cashflows',
                queryset=SingleCashFlow.objects.filter(
                    company=self.request.user.company
                ).select_related(
                    'company',
                    'generator',
                    'buy_currency',
                    'sell_currency',
                    'lock_side'
                ).prefetch_related(
                    'tickets'
                )
            ),
            Prefetch(
                'cashflow_generator__cashflows__tickets'
            )
        )
        return qs

    @extend_schema(
        description="Retrieve list of company's payment records",
        responses={
            status.HTTP_200_OK: PaymentSerializer(many=True),
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def list(self, request):
        try:
            return super().list(request)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Create new company's payment",
        request=PaymentSerializer,
        responses={
            status.HTTP_201_CREATED: PaymentSerializer,
            status.HTTP_400_BAD_REQUEST: PaymentValidationErrorSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def create(self, request):
        try:
            request.data['user'] = request.user
            serializer = PaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            payment_obj = PaymentService.create_payment(company=request.user.company,
                                                create_user=request.user,
                                                 **serializer.validated_data)
            payment_approval_svc = PaymentApprovalService(company=request.user.company)
            approvers, min_approvers = payment_approval_svc.\
                get_payment_approval_detail(payment=payment_obj)
            payment_obj.approvers = approvers
            payment_obj.min_approvers = min_approvers
            payment_obj.assigned_approvers = payment_approval_svc.\
                get_payment_assigned_approvers(payment=payment_obj)
            resp_serializer = PaymentSerializer(payment_obj)
            return Response(resp_serializer.data, status=status.HTTP_201_CREATED)
        except srz.ValidationError as e:
            error_resp = PaymentResponseUtils().create_validation_error_response(e=e)
            return Response(error_resp, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Retrieve company's payment detail by id",
        request=PaymentSerializer,
        responses={
            status.HTTP_200_OK: PaymentSerializer,
            status.HTTP_404_NOT_FOUND: PaymentErrorSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def retrieve(self, request, pk:int):
        try:
            payment = get_object_or_404(self.get_queryset(), pk=pk)
            payment_approval_svc = PaymentApprovalService(company=request.user.company)
            approvers, min_approvers = payment_approval_svc.get_payment_approval_detail(payment=payment)
            payment.approvers = approvers
            payment.min_approvers = min_approvers
            payment.assigned_approvers = payment_approval_svc.\
                get_payment_assigned_approvers(payment=payment)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404 as e:
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Update company's payment detail by id",
        request=PaymentSerializer,
        responses={
            status.HTTP_200_OK: PaymentSerializer,
            status.HTTP_400_BAD_REQUEST: PaymentValidationErrorSerializer,
            status.HTTP_404_NOT_FOUND: PaymentErrorSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def update(self, request, pk:int = None):
        try:
            payment = get_object_or_404(self.get_queryset(), pk=pk)

            request.data['user'] = request.user
            serializer = PaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            payment_obj = PaymentService.update_payment(
                payment=payment,
                company=request.user.company,
                **serializer.validated_data
            )
            payment_obj = get_object_or_404(self.get_queryset(), pk=payment_obj.pk)
            payment_approval_svc = PaymentApprovalService(company=request.user.company)
            approvers, min_approvers = payment_approval_svc.\
                get_payment_approval_detail(payment=payment_obj)
            payment_obj.approvers = approvers
            payment_obj.min_approvers = min_approvers
            payment_obj.assigned_approvers = payment_approval_svc.\
                get_payment_assigned_approvers(payment=payment_obj)
            resp_serializer = PaymentSerializer(payment_obj)
            return Response(resp_serializer.data, status=status.HTTP_200_OK)
        except srz.ValidationError as e:
            error_resp = PaymentResponseUtils().create_validation_error_response(e=e)
            return Response(error_resp, status=status.HTTP_400_BAD_REQUEST)
        except Http404 as e:
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Remove company's payment by id",
        responses={
            status.HTTP_200_OK: PaymentSerializer,
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_404_NOT_FOUND: PaymentErrorSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def destroy(self, request, pk:int = None):
        try:
            payment = get_object_or_404(self.get_queryset(), pk=pk)
            payment = PaymentService.delete_payment(payment=payment)

            if payment:
                resp_serializer = PaymentSerializer(payment)
                return Response(resp_serializer.data, status=status.HTTP_200_OK)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404 as e:
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            if isinstance(e.args[0], dict):
                code = e.args[0]['failed'][0]['status']
                return Response(e.args[0], status=code)
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PaymentCashflowViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    pagination_class = None
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    serializer_class = InstallmentCashflowSerializer
    ordering_fields = ['pay_date']
    ordering = ['-pay_date']

    def get_payment(self) -> Payment:
        payment = get_object_or_404(
            Payment.objects.filter(cashflow_generator__company=self.request.user.company),
            pk=self.kwargs['payment_id']
        )
        if not payment.cashflow_generator.installment and not payment.cashflow_generator.recurring:
            raise BadRequest("Payment is not an installment or a recurring type")
        return payment

    def get_queryset(self):
        payment = self.get_payment()
        return SingleCashFlow.objects.filter(generator=payment.cashflow_generator)\
            .select_related('lock_side', 'buy_currency', 'sell_currency')

    @extend_schema(
        description="Retrieve list of company's cashflow payment records that tied to a certain payment",
        responses={
            status.HTTP_200_OK: InstallmentCashflowSerializer(many=True),
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def list(self, request, payment_id:int):
        try:
            return super().list(request)
        except BadRequest as e:
            return Response({"msg": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Create new cashflow payment record that will be tied to a certain payment",
        request=InstallmentCashflowSerializer,
        responses={
            status.HTTP_201_CREATED: InstallmentCashflowSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def create(self, request, payment_id:int):
        serializer = InstallmentCashflowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = self.get_payment()
            installment = PaymentCashflowService().create_cashflow(
                payment=payment,
                **serializer.validated_data
            )
            resp_serializer = InstallmentCashflowSerializer(installment)

            return Response(resp_serializer.data, status=status.HTTP_201_CREATED)
        except BadRequest as e:
            return Response({"msg": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Retrieve company's cashflow payment detail by id that tied to a certain payment",
        request=InstallmentCashflowSerializer,
        responses={
            status.HTTP_200_OK: InstallmentCashflowSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def retrieve(self, request, payment_id:int, cashflow_id:str):
        try:
            installment = get_object_or_404(self.get_queryset(), cashflow_id=cashflow_id)
            serializer = InstallmentCashflowSerializer(installment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except BadRequest as e:
            return Response({"msg": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Update company's cashflow payment detail by id that tied to a certain payment",
        request=InstallmentCashflowSerializer,
        responses={
            status.HTTP_200_OK: InstallmentCashflowSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def update(self, request, payment_id:int, cashflow_id:str):
        serializer = InstallmentCashflowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = self.get_payment()

            cashflow = get_object_or_404(self.get_queryset(), cashflow_id=cashflow_id)
            cashflow_obj = PaymentCashflowService().update_cashflow(
                cashflow = cashflow,
                **serializer.validated_data
            )
            resp_serializer = InstallmentCashflowSerializer(cashflow_obj)

            return Response(resp_serializer.data, status=status.HTTP_200_OK)
        except BadRequest as e:
            return Response({"msg": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        description="Remove company's cashflow payment by id that tied to a certain payment",
        responses={
            status.HTTP_200_OK: InstallmentCashflowSerializer,
            status.HTTP_204_NO_CONTENT: None,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer
        }
    )
    def destroy(self, request, payment_id:int, cashflow_id:str):
        cashflow = get_object_or_404(self.get_queryset(), cashflow_id=cashflow_id)
        try:
            payment = self.get_payment()

            cashflow_obj = PaymentCashflowService().delete_cashflow(
                payment=payment,
                cashflow=cashflow
            )

            if cashflow_obj:
                resp_serializer = InstallmentCashflowSerializer(cashflow_obj)
                return Response(resp_serializer.data, status=status.HTTP_200_OK)

            return Response(status=status.HTTP_204_NO_CONTENT)
        except BadRequest as e:
            return Response({"msg": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
