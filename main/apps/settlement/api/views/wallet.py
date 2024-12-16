import logging

from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from main.apps.settlement.api.filters.wallet import WalletFilter
from main.apps.settlement.api.permissions import WalletBelongsToCompany
from main.apps.settlement.api.serializers.wallet import WalletSerializer, WalletUpdateSerializer
from main.apps.settlement.models import Wallet
from main.apps.settlement.services.wallet_notif import WalletActionService

logger = logging.getLogger(__name__)


class WalletViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'wallet_id'
    lookup_url_kwarg = 'wallet_id'
    filter_class = WalletFilter
    filter_backends = (filters.DjangoFilterBackend,)

    def get_queryset(self):
        company = self.request.user.company
        return self.queryset.filter(company=company)

    @extend_schema(
        tags=["Settlement"],
        summary="List Wallets",
        description="Endpoint for listing all wallets for a company",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Settlement"],
        summary="Retrieve Wallets",
        description="Endpoint for retrieving a specific wallet",
    )
    def retrieve(self, request, *args, **kwargs):
        self.permission_classes = [IsAuthenticated, WalletBelongsToCompany]
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Settlement"],
        summary="Update Wallets",
        description="Update wallet nickname or default flag",
        request=WalletUpdateSerializer,
        responses={
            status.HTTP_200_OK: WalletSerializer
        }
    )
    def update(self, request, *args, **kwargs):
        self.permission_classes = [IsAuthenticated, WalletBelongsToCompany]
        instance:Wallet = self.get_object()

        payload:dict = request.data

        if payload.get('default', False):
            Wallet.objects.filter(company=instance.company)\
                .update(default=False)

        serializer = self.get_serializer(instance, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @extend_schema(
        tags=["Settlement"],
        summary="Send Request for Wallet Removal",
        description=f"Send request notification for wallet "
                    f"removal and set its status to pending",
    )
    def destroy(self, request, *args, **kwargs):
        self.permission_classes = [IsAuthenticated, WalletBelongsToCompany]
        instance:Wallet = self.get_object()
        try:
            if instance.status == Wallet.WalletStatus.ACTIVE:
                wallet_svc =  WalletActionService(wallet=instance)
                wallet_svc.send_deletion_notification()
                instance.status = Wallet.WalletStatus.PENDING
                instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(e, exc_info=True)
            return Response(data={
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
