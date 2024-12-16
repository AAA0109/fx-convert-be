import django_filters
from django_filters import FilterSet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from main.apps.account.api.serializers.cashflow import *
from main.apps.account.models import Account
from main.apps.core.utils.api import *


# ====================================================================
#  Cashflows
# ====================================================================

class CashflowFilter(FilterSet):
    installment__installment_name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = CashFlow
        fields = {
            'account': ['exact'],
            'installment': ['exact'],

            'status': ['iexact', 'in'],
            'created': ['gte', 'gt', 'lte', 'lt'],
            'modified': ['gte', 'gt', 'lte', 'lt']
        }


class CashflowsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    serializer_class = CashflowSerializer
    filter_class = CashflowFilter

    def get_queryset(self):
        try:
            qs = CashFlow.objects.filter(account__company_id=self.request.user.company_id)
            return qs.select_related('currency', 'account', 'installment', 'draft', 'draft__currency').prefetch_related('draftfxforwardposition_set', 'fxforwardposition_set')
        except Exception as e:
            return CashFlow.objects.none()
