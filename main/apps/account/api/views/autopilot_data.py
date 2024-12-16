from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from main.apps.account.api.serializers.autopilot_data import AutopilotDataSerializer, AutopilotDataRequestSerializer
from main.apps.account.models import AutopilotData, Account
from main.apps.core.utils.api import HasCompanyAssociated


class AutopilotDataViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = AutopilotDataSerializer
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    def get_queryset(self):
        return AutopilotData.objects.filter(account=self.kwargs['account_pk'])

    def perform_create(self, serializer):
        account = get_object_or_404(Account, pk=self.kwargs['account_pk'])
        serializer.save(account=account)

    @extend_schema(
        request=AutopilotDataRequestSerializer
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
