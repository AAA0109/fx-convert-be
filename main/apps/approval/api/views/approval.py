import logging
from typing import List
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from main.apps.account.models.user import User
from main.apps.approval.api.serializers.approval import (
    ApproveRequestSerializer,
    ApproverRequestSerializer,
    ApproverResponseSerializer,
    RequestApprovalSerializer)
from main.apps.approval.services.approval import ApproverProvider
from main.apps.approval.services.payment_approval import PaymentApprovalService
from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.core.utils.api import HasCompanyAssociated, get_response_from_action_status
from main.apps.payment.api.serializers.payment import PaymentErrorSerializer
from main.apps.payment.models.payment import Payment
from main.apps.payment.services.error_utils import PaymentResponseUtils
from main.apps.util import ActionStatus


logger = logging.getLogger(__name__)


class ApproverAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=ApproverRequestSerializer,
        responses={
            status.HTTP_200_OK: ApproverResponseSerializer,
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = ApproverRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        approver_provider = ApproverProvider(request.user.company)
        approvers = approver_provider.get_transaction_approvers(currency=validated_data.get('lock_side_currency'),
                                                                amount=float(validated_data.get('lock_side_amount')),
                                                                value_date=validated_data.get('value_date'))

        response_serializer = ApproverResponseSerializer({'approvers': approvers})
        return Response(response_serializer.data, status.HTTP_200_OK)


class RequestPaymentApprovalAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        request=RequestApprovalSerializer,
        responses={
            status.HTTP_200_OK: ActionStatusSerializer,
            status.HTTP_403_FORBIDDEN: ActionStatusSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer,
        }
    )
    def post(self, request:Request, *args, **kwargs):
        serializer = RequestApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        approvers:List[User] = validated_data.get('approver_user_ids', [])
        payment:Payment = validated_data.get('payment_id', None)

        for user in approvers:
            if user.company != request.user.company or user.company != payment.create_user.company:
                return get_response_from_action_status(
                    http_status=status.HTTP_403_FORBIDDEN,
                    action_status=ActionStatus(status=ActionStatus.Status.ERROR,
                                            message="Approver from different company exist",
                                            code=status.HTTP_403_FORBIDDEN))

        try:
            approval_svc = PaymentApprovalService(company=request.user.company)
            approval_svc.request_approval(payment=payment, approvers=approvers)
            return get_response_from_action_status(
                http_status=status.HTTP_200_OK,
                action_status=ActionStatus(status=ActionStatus.Status.SUCCESS,
                                           message='Success',
                                           code=status.HTTP_200_OK))
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApproveApprovalRequestAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        parameters=[ApproveRequestSerializer],
        responses={
            status.HTTP_200_OK: ActionStatusSerializer,
            status.HTTP_403_FORBIDDEN: ActionStatusSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: PaymentErrorSerializer,
        }
    )
    def get(self, request:Request, *args, **kwargs):
        serializer = ApproveRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        payment:Payment = validated_data.get('payment_id', None)

        if payment.create_user.company != request.user.company:
            return get_response_from_action_status(
                http_status=status.HTTP_403_FORBIDDEN,
                action_status=ActionStatus(status=ActionStatus.Status.ERROR,
                                           message="Can't approver payment for different company",
                                           code=status.HTTP_403_FORBIDDEN))

        approvers = [user for user in
                     [payment.cashflow_generator.approver_1, payment.cashflow_generator.approver_2] \
                      if user is not None]

        if len(approvers) == 0 or request.user not in approvers:
            return get_response_from_action_status(
                http_status=status.HTTP_403_FORBIDDEN,
                action_status=ActionStatus(status=ActionStatus.Status.ERROR,
                                           message="Can't approver payment",
                                           code=status.HTTP_403_FORBIDDEN))

        try:
            approval_svc = PaymentApprovalService(company=request.user.company)
            approval_svc.approve_request(payment=payment, user=request.user)
            return get_response_from_action_status(
                http_status=status.HTTP_200_OK,
                action_status=ActionStatus(status=ActionStatus.Status.SUCCESS,
                                           message='Success',
                                           code=status.HTTP_200_OK))
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
