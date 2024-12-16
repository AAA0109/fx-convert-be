from rest_framework.permissions import BasePermission


class BeneficiaryBelongsToCompany(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.company == request.user.company


class WalletBelongsToCompany(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.company == request.user.company
