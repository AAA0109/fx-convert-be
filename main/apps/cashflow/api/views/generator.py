from datetime import date

from drf_spectacular.utils import extend_schema, OpenApiExample
from idempotency_key.decorators import idempotency_key
from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from main.apps.cashflow.api.serializers.generator import CashFlowGeneratorSerializer
from main.apps.cashflow.models import CashFlowGenerator
from main.apps.core.utils.api import *


class CashFlowGeneratorViewSet(mixins.CreateModelMixin,
                               mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.DestroyModelMixin,
                               viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    serializer_class = CashFlowGeneratorSerializer
    lookup_field = 'cashflow_id'

    def check_object_permissions(self, request, obj):
        if request.user.company != obj.company:
            raise PermissionDenied(detail="You do not have permission to view this strategy")

    def get_queryset(self):
        try:
            qs = CashFlowGenerator.objects.filter(company=self.request.user.company)
            return qs.select_related('sell_currency', 'buy_currency')
        except Exception as e:
            return CashFlowGenerator.objects.none()

    def perform_create(self, serializer):
        # Set `user_field` to `request.user.x` before saving the instance
        serializer.save(company=self.request.user.company)

    def perform_update(self, serializer):
        # Optionally, update `user_field` to `request.user.x` before saving the instance
        serializer.save(company=self.request.user.company)

    @extend_schema(
        tags=['Cashflow'],
        summary="Create Cashflow",
        description="Endpoint for creating and staging a new FX exposure.",
        examples=[
            OpenApiExample(
                name='Create Cashflow',
                value={
                    "name": "MXN Developer Salary",
                    "description": "Salary for developers in mexico.",
                    "buy_currency": "USD",
                    "sell_currency": "MXN",
                    "lock_side": "USD",
                    "amount": 10000.0,
                    "value_date": date.today().isoformat(),
                    "is_draft": True,
                    "self_directed": True
                },
                request_only=True
            ),
        ],
        responses={
            status.HTTP_200_OK: CashFlowGeneratorSerializer
        }
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=['Cashflow'],
        summary="List Cashflows",
        description="Endpoint for retrieving a list of all cashflows"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['Cashflow'],
        summary="Retrieve Cashflow",
        description="Endpoint for retrieving a specific, single cashflow"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=['Cashflow'],
        summary="Update Cashflow",
        description='Endpoint for replacing a specific, single cashflow. '
                    'This can only be called on a cashflow that is in "Draft" status'
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != CashFlowGenerator.Status.DRAFT:
            raise ValidationError("Unable to update cashflow that is not in 'draft' status.")
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=['Cashflow'],
        summary="Partial Update Cashflow",
        description='Endpoint for updating a specific, single cashflow. '
                    'This can only be called on a cashflow that is in "Draft" status'
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != CashFlowGenerator.Status.DRAFT:
            raise ValidationError("Unable to update cashflow that is not in 'draft' status.")
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=['Cashflow'],
        summary="Delete Cashflow",
        description='Endpoint for deleting a specific, single cashflow. '
                    'This can only be called on a cashflow that is in "Draft" status'
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != CashFlowGenerator.Status.DRAFT:
            raise ValidationError("Unable to delete cashflow that is not in 'draft' status")
        return super().destroy(request, *args, **kwargs)
