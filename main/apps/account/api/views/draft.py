import django_filters
from django_filters import FilterSet

from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated

from main.apps.account.api.serializers.cashflow import DraftCashflowSerializer
from main.apps.account.models import DraftCashFlow
from main.apps.core.utils.api import HasCompanyAssociated


class DraftCashflowFilter(FilterSet):
    installment__installment_name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = DraftCashFlow
        fields = {
            'account': ['exact'],
            'installment': ['exact'],

            'created': ['gte', 'gt', 'lte', 'lt'],
            'modified': ['gte', 'gt', 'lte', 'lt']
        }


class DraftCashflowsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    serializer_class = DraftCashflowSerializer
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
    filter_class = DraftCashflowFilter

    def get_queryset(self):
        try:
            return DraftCashFlow.objects.filter(company=self.request.user.company)
        except Exception as e:
            return DraftCashFlow.objects.none()
