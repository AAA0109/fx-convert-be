from datetime import datetime
import logging
from typing import List, Tuple
from django.db import transaction
from django.http import HttpRequest
from main.apps.account.models.company import Company
from main.apps.account.models.user import User
from main.apps.approval.models.approval import ApprovalMethod, CompanyApprovalBypass
from main.apps.approval.services.approval import ApproverProvider, CompanyApprovalService
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.cashflow.models.generator import CashFlowGenerator
from main.apps.notification.utils.email import send_approval_request_email, send_approved_request_email
from main.apps.payment.models import Payment
from main.apps.payment.services.payment_execution import PaymentExecutionService


logger = logging.getLogger(__name__)


class PaymentApprovalService:
    company:Company

    def __init__(self, company:Company) -> None:
        self.company = company

    def request_approval(self, payment:Payment, approvers:List[User]):
        approval_svc = CompanyApprovalService(company=self.company)
        approval_setting = approval_svc.get_company_approval_setting()

        cashflow_generator = payment.cashflow_generator

        with transaction.atomic():
            if approval_setting and approval_setting.approval_method == ApprovalMethod.APPROVAL_REQUIRED:
                cashflow_generator.approval_method = approval_setting.approval_method
                cashflow_generator.approval_trigger = approval_setting.approval_trigger
                cashflow_generator.is_dual_approval = approval_setting.enable_dual_approval
                if len(approvers) >= 1:
                    cashflow_generator.approver_1 = approvers[0]
                if len(approvers) == 2:
                    cashflow_generator.approver_2 = approvers[1]
                if cashflow_generator.status == CashFlowGenerator.Status.DRAFT:
                    cashflow_generator.status = CashFlowGenerator.Status.PENDAUTH
                cashflow_generator.save()

                if payment.payment_status == Payment.PaymentStatus.DRAFTING:
                    payment.payment_status = Payment.PaymentStatus.PENDAUTH
                payment.save()
                try:
                    send_approval_request_email(payment=payment)
                except Exception as e:
                    logger.error(f'Error sending payment approval request email: {str(e)}', exc_info=True)

    def approve_request(self, payment:Payment, user:User):
        cashflow_generator = payment.cashflow_generator

        if cashflow_generator.status == CashFlowGenerator.Status.PENDAUTH:
            with transaction.atomic():
                if user == cashflow_generator.approver_1:
                    cashflow_generator.approval_date_1 = datetime.now()
                elif user == cashflow_generator.approver_2:
                    cashflow_generator.approval_date_2 = datetime.now()

                if (cashflow_generator.is_dual_approval and cashflow_generator.approval_date_1 is not None \
                    and cashflow_generator.approval_date_2 is not None) or \
                    (not cashflow_generator.is_dual_approval and cashflow_generator.approval_date_1 is not None):
                    cashflow_generator.status = CashFlowGenerator.Status.APPROVED
                    payment.payment_status = Payment.PaymentStatus.APPROVED

                cashflow_generator.save()
                payment.save()

                # Execute payment and send email after all approvers approve the request
                if cashflow_generator.status == CashFlowGenerator.Status.APPROVED and \
                    payment.payment_status == Payment.PaymentStatus.APPROVED:
                    try:
                        send_approved_request_email(payment=payment)
                    except Exception as e:
                        logger.error(f'Error sending payment approved email: {str(e)}', exc_info=True)

                    request = HttpRequest()
                    request.user = payment.create_user

                    try:
                        execution_service = PaymentExecutionService(payment=payment, request=request)
                        response = execution_service.execute()
                    except Exception as e:
                        logger.error(f'Error executing payment after approval: {str(e)}', exc_info=True)

    def get_payment_approval_detail(self, payment:Payment) -> Tuple[List[User], int]:
        approver_provider = ApproverProvider(payment.create_user.company)
        approval_svc = CompanyApprovalService(company=payment.create_user.company)
        approval_setting = approval_svc.get_company_approval_setting()

        if approval_setting is None:
            return [], 0

        approvers = []
        if payment.cashflow_generator.recurring == False and payment.cashflow_generator.installment == False:
            approvers = approver_provider.get_transaction_approvers(currency=payment.cashflow_generator.lock_side,
                                                                    amount=payment.cashflow_generator.amount,
                                                                    value_date=payment.cashflow_generator.value_date)
        else:
            cashflows = SingleCashFlow.objects.filter(generator=payment.cashflow_generator)
            total_amount = 0
            value_date = payment.cashflow_generator.value_date
            if value_date is None:
                value_date = cashflows[0].pay_date
            for cashflow in cashflows:
                total_amount += cashflow.amount
            approvers = approver_provider.get_transaction_approvers(currency=payment.cashflow_generator.lock_side,
                                                                    amount=total_amount,
                                                                    value_date=value_date)

        if len(approvers) == 0:
            return approvers, 0
        # exclude payment creator from list of approver
        approvers = list(filter(lambda x: x != payment.create_user, approvers))
        return approvers, 2 if approval_setting.enable_dual_approval else 1

    def get_payment_assigned_approvers(self, payment:Payment) -> List[User]:
        assigned_approvers = []
        if payment.cashflow_generator.approver_1 is not None and \
            payment.cashflow_generator.approval_date_1 is None:
            assigned_approvers.append(payment.cashflow_generator.approver_1)
        if payment.cashflow_generator.approver_2 is not None and \
            payment.cashflow_generator.approval_date_2 is None:
            assigned_approvers.append(payment.cashflow_generator.approver_2)
        return assigned_approvers

    def can_bypass_approval(self, user:User) -> bool:
        if user.company is None:
            return False

        approval_svc = CompanyApprovalService(company=user.company)
        approval_setting = approval_svc.get_company_approval_setting()

        if approval_setting is None or approval_setting.approval_method == ApprovalMethod.NO_APPROVAL:
            return True

        bypassers = CompanyApprovalBypass.objects.filter(company=user.company)\
            .values_list('user_id', flat=True)

        if user.pk in bypassers:
            return True
        return False
