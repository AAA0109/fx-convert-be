from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer, OpenApiExample
from idempotency_key.decorators import idempotency_key
from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from main.apps.core.api.views.mixins import MultipleFieldLookupMixin
from main.apps.strategy.api.serializers.strategy import StrategiesSerializer
from main.apps.cashflow.models import SingleCashFlow
from main.apps.strategy.models import HedgingStrategy
from main.apps.core.utils.api import *


class StrategyViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      mixins.DestroyModelMixin,
                      mixins.UpdateModelMixin,
                      MultipleFieldLookupMixin,
                      viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    serializer_class = StrategiesSerializer
    lookup_field = 'strategy_id'
    lookup_fields = ('strategy_id', 'slug')

    def get_queryset(self):
        try:
            qs = HedgingStrategy.objects.filter(company=self.request.user.company)
            return qs.select_related('company', 'buy_currency', 'sell_currency')
        except Exception as e:
            return SingleCashFlow.objects.none()

    def perform_create(self, serializer):
        # Optionally, update `user_field` to `request.user.x` before saving the instance
        serializer.validated_data['company'] = self.request.user.company
        return super().perform_create(serializer)

    def perform_update(self, serializer):
        # Optionally, update `user_field` to `request.user.x` before saving the instance
        # serializer.save(company=self.request.user.company)
        return super().perform_update(serializer)

    def check_object_permissions(self, request, obj):
        if request.user.company != obj.company:
            raise PermissionDenied(detail="You do not have permission to view this strategy")

    @extend_schema(
        tags=["Strategy"],
        summary="Create Strategy",
        description="Endpoint for creating a new strategy.",
        examples=[
            OpenApiExample(
                name="Self-Directed Strategy",
                value={
                    "name": "Self-Directed Strategy",
                    "description": "100% Hedge of all JPY exposure",
                    "buy_currency": "USD",
                    "sell_currency": "JPY",
                    "lock_side": "JPY",
                    "strategy": "selfdirected",
                },
                request_only=True
            ),
            OpenApiExample(
                name="Autopilot Strategy",
                value={
                    "name": "Autopilot Strategy",
                    "description": "Salary lock with 50% risk reduction with a 80% upper bound and a 20% lower bound.",
                    "buy_currency": "USD",
                    "sell_currency": "EUR",
                    "lock_side": "EUR",
                    "risk_reduction": 0.5,
                    "upper_bound": 0.8,
                    "lower_bound": 0.2,
                    "strategy": "autopilot",
                },
                request_only=True
            ),
            OpenApiExample(
                name="Parachute Strategy",
                value={
                    "name": "Parachute Strategy",
                    "description": "Rate lock with a lower limit of 4%, lower and upper probability thread hold of 97%",
                    "buy_currency": "USD",
                    "sell_currency": "MXN",
                    "lock_side": "MXN",
                    "lower_limit": 0.04,
                    "strategy": "parachute",
                },
                request_only=True
            ),
            # OpenApiExample(
            #     name="ZeroGravity Strategy",
            #     value={
            #         "name": "Zero-Gravity Strategy",
            #         "description": "Portfolio hedging with vol reduction target of 50%, $200000 margin budget, "
            #                        "using min var method and a max horizon of 20 years",
            #         "currency": "JPY",
            #         "margin_budget": 200000,
            #         "method": "MIN_VAR",
            #         "max_horizon_days": 7300,
            #         "vol_target_reduction": 0.5,
            #         "strategy": "zerogravity"
            #     }
            # )
        ],
        responses={
            status.HTTP_200_OK: StrategiesSerializer
        }
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["Strategy"],
        summary="List Strategies",
        description="Endpoint for retrieving a list of all strategies for the current user's company"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Strategy"],
        summary="Retrieve Strategy",
        description="Endpoint for retrieving a specific cashflow that belongs to the user's company."
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Strategy"],
        summary="Replace Strategy",
        description="Endpoint for replacing a specific strategy belonging to the user's company."
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["Strategy"],
        summary="Update Strategy",
        description="Endpoint for updating a specific strategy belonging to the user's company."
    )
    def partial_update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["Strategy"],
        summary="Delete Strategy",
        description="Endpoint for deleting a specific strategy that belongs to the user's company."
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
