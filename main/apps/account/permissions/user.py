from rest_framework import permissions

from main.apps.account.models import User


class UserIsAdmin(permissions.BasePermission):
    message = "User is not admin"

    def has_permission(self, request, view):
        try:
            user_groups = [group.name for group in request.user.groups.all()]
            if User.UserGroups.CUSTOMER_ADMIN in user_groups:
                return True
            return False
        except Exception as e:
            return False


class UserInSameCompany(permissions.BasePermission):
    message = "User is not in the same company"

    def has_permission(self, request, view):
        try:
            user = request.user
            view_user = None
            if 'id' in view.kwargs:
                view_user = User.objects.get(pk=view.kwargs['id'])
            if 'pk' in view.kwargs:
                view_user = User.objects.get(pk=view.kwargs['pk'])
            if 'user_pk' in view.kwargs:
                view_user = User.objects.get(pk=view.kwargs['user_pk'])
            if view_user is None:
                return False
            return user.company.pk == view_user.company.pk
        except Exception as e:
            return False
