from typing import Optional

from rest_framework.response import Response
from rest_framework import permissions

from main.apps.util import ActionStatus
from main.apps.account.models.user import User
from main.apps.account.models.cashflow import CashFlow
from main.apps.account.models.installment_cashflow import InstallmentCashflow


def get_response_from_action_status(http_status: int, action_status: ActionStatus,
                                    data: Optional[object] = None) -> Response:
    return Response({
        'message': action_status.message,
        'status': action_status.status.name,
        'code': action_status.code,
        'data': data
    }, http_status)


def validate_company_id(user: User, company_id):
    if user.company.id == company_id:
        return True
    return False


def validate_account_id(user: User, account_id):
    if user.accounts.filter(account_id=account_id).count():
        return True
    return False


def validate_cashflow_id(user: User, cashflow_id: int, cashflow_type: str):
    if cashflow_type == 'raw':
        cashflow = CashFlow.objects.get(id=cashflow_id)
    elif cashflow_type == 'installment':
        cashflow = InstallmentCashflow.objects.get(id=cashflow_id)

    if cashflow.objects.filter(account__in=user.accounts).count():
        return True

    return False


class HasCompanyAssociated(permissions.BasePermission):
    message = 'User does not have a company.'

    def has_permission(self, request, view):
        try:
            company = request.user.company
            return company is not None
        except Exception as e:
            return False


class UserBelongsToCompany(permissions.BasePermission):
    message = 'User does not belong to company'

    def has_permission(self, request, view):
        try:
            company = request.user.company
            if "pk" in view.kwargs:
                return company.id == int(view.kwargs["pk"])
            if "company_pk" in view.kwargs:
                return company.id == int(view.kwargs["company_pk"])
        except Exception as e:
            return False


class BrokerAccountBelongsToUser(permissions.BasePermission):
    message = "Broker account does not belong to the user's company"

    def has_permission(self, request, view):
        try:
            company = request.user.company
            broker_account_id = request.query_params.get('broker_account_id')
            if broker_account_id is None:
                self.message = "Broker account ID is missing"
                return False
            if company.broker_accounts.filter(pk=broker_account_id).count() > 0:
                return True
            return False
        except Exception as e:
            return False


class IsAccountValidated(permissions.BasePermission):
    message = 'Request does not have a valid account ID.'

    def has_permission(self, request, view):
        try:
            account_id = int(view.kwargs.get('account_pk', None))

            # account_id should not be None
            if account_id is None:
                self.message = "Account ID is required and cannot be None."
                return False

            # current user has access to this account
            return request.user.accounts.filter(pk=account_id).count() > 0
        except Exception:
            return False


class IsAccountOwner(permissions.BasePermission):
    message = 'User is not the company account owner'

    def has_permission(self, request, view):
        try:
            company = request.user.company
            if company.account_owner.pk == request.user.pk:
                return True
        except Exception:
            return False
        return False
