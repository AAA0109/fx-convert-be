from rest_framework.permissions import BasePermission


class IsInternalSystemUser(BasePermission):
    """
    Allows access only to internal system users
    """

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.groups.filter(name="system_internal").exists()
        )
