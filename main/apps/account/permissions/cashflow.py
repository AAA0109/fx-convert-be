from rest_framework import permissions

from main.apps.account.models import User


class CanApproveCashflow(permissions.BasePermission):
    message = 'User does not have permission to approve cashflow'

    def has_permission(self, request, view):
        try:
            user_groups = [group.name for group in request.user.groups.all()]
            if User.UserGroups.CUSTOMER_ADMIN in user_groups or User.UserGroups.CUSTOMER_MANAGER in user_groups:
                return True
            return False
        except Exception as e:
            return False

