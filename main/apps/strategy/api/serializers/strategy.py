from enum import Enum

from polymorphic.base import PolymorphicModelBase
from polymorphic.models import PolymorphicModel
from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer

from main.apps.core.constants import TARGET_VARIANCE_HELP_TEXT, RISK_BEFORE_HEDGE_HELP_TEXT, \
    REMAINING_RISK_AFTER_HEDGE_HELP_TEXT, MAX_COST_HELP_TEXT, LOCK_SIDE_HELP_TEXT, CURRENCY_HELP_TEXT
from main.apps.core.models.choices import LockSides
from main.apps.strategy.models import (
    HedgingStrategy,
    AutopilotHedgingStrategy,
    ZeroGravityHedgingStrategy,
    ParachuteHedgingStrategy, SelfDirectedHedgingStrategy,
)
from main.apps.currency.models import Currency


class Strategy(Enum):
    SelfDirected = "selfdirected"
    Autopilot = "autopilot"
    ZeroGravity = "zerogravity"
    Parachute = "parachute"


class HedgingStrategySerializer(serializers.ModelSerializer):
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=CURRENCY_HELP_TEXT)
    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=LOCK_SIDE_HELP_TEXT)

    class Meta:
        model = HedgingStrategy
        fields = (
            'strategy_id',
            'slug',
            'status',
            'buy_currency',
            'sell_currency',
            'lock_side',
            'name',
            'description',
            'created',
            'modified'
        )
        read_only_fields = (
            'status',
            'created',
            'modified'
        )


class SelfDirectedSerializer(serializers.ModelSerializer):
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=CURRENCY_HELP_TEXT)
    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=LOCK_SIDE_HELP_TEXT)

    class Meta:
        model = SelfDirectedHedgingStrategy
        fields = (
            'strategy_id',
            'slug',
            'status',
            'buy_currency',
            'sell_currency',
            'lock_side',
            'name',
            'description',
            'created',
            'modified',
        )
        read_only_fields = (
            'slug',
            'status',
            'created',
            'modified'
        )


class AutopilotSerializer(serializers.ModelSerializer):
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=CURRENCY_HELP_TEXT)
    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=LOCK_SIDE_HELP_TEXT)
    upper_target = serializers.FloatField(help_text=TARGET_VARIANCE_HELP_TEXT, required=False)
    lower_target = serializers.FloatField(help_text=TARGET_VARIANCE_HELP_TEXT, required=False)
    risk_before_hedge = serializers.FloatField(help_text=RISK_BEFORE_HEDGE_HELP_TEXT, read_only=True)
    remaining_risk_after_hedge = serializers.FloatField(help_text=REMAINING_RISK_AFTER_HEDGE_HELP_TEXT, read_only=True)

    class Meta:
        model = AutopilotHedgingStrategy
        fields = (
            'strategy_id',
            'slug',
            'status',
            'buy_currency',
            'sell_currency',
            'lock_side',
            'name',
            'description',
            'created',
            'modified',
            "risk_reduction",
            "upper_target",
            "lower_target",
            "risk_before_hedge",
            "remaining_risk_after_hedge"
        )
        read_only_fields = (
            'slug',
            'status',
            'created',
            'modified',
            'risk_before_hedge',
            'remaining_risk_after_hedge'
        )


class ParachuteSerializer(serializers.ModelSerializer):
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=CURRENCY_HELP_TEXT)
    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=LOCK_SIDE_HELP_TEXT)
    risk_before_hedge = serializers.FloatField(help_text=RISK_BEFORE_HEDGE_HELP_TEXT, read_only=True)
    max_cost = serializers.FloatField(help_text=MAX_COST_HELP_TEXT, read_only=True)

    class Meta:
        model = ParachuteHedgingStrategy
        fields = (
            'strategy_id',
            'slug',
            'status',
            'name',
            'description',
            'buy_currency',
            'sell_currency',
            'lock_side',
            'created',
            'modified',
            "lower_limit",
            "risk_before_hedge",
            "max_cost"
        )
        read_only_fields = (
            'slug',
            'status',
            'created',
            'modified',
            "risk_before_hedge",
            "max_cost"
        )


class ZeroGravitySerializer(serializers.ModelSerializer):
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                                 help_text=CURRENCY_HELP_TEXT)
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=CURRENCY_HELP_TEXT)
    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all(),
                                               help_text=LOCK_SIDE_HELP_TEXT)

    class Meta:
        model = ZeroGravityHedgingStrategy
        fields = (
            'strategy_id',
            'slug',
            'status',
            'buy_currency',
            'sell_currency',
            'name',
            'description',
            'created',
            'modified',
            "margin_budget",
            "method",
            'max_horizon_days',
            'vol_target_reduction',
            'var_95_exposure_ratio',
            'var_95_exposure_window'
        )
        read_only_fields = (
            'slug',
            'status',
            'created',
            'modified'
        )


class StrategiesSerializer(PolymorphicSerializer):
    resource_type_field_name = 'strategy'
    model_serializer_mapping = {
        SelfDirectedHedgingStrategy: SelfDirectedSerializer,
        AutopilotHedgingStrategy: AutopilotSerializer,
        ParachuteHedgingStrategy: ParachuteSerializer,
        # TODO: Hiding ZeroGravity until we are ready
        # ZeroGravityHedgingStrategy: ZeroGravitySerializer
    }

    def to_resource_type(self, model_or_instance):
        strategy_map = {
            AutopilotHedgingStrategy: Strategy.Autopilot.value,
            ParachuteHedgingStrategy: Strategy.Parachute.value,
            ZeroGravityHedgingStrategy: Strategy.ZeroGravity.value,
            SelfDirectedHedgingStrategy: Strategy.SelfDirected.value,
        }

        if isinstance(model_or_instance, PolymorphicModelBase):
            if model_or_instance in strategy_map:
                return strategy_map[model_or_instance]
            else:
                raise serializers.ValidationError("Invalid strategy")

        if isinstance(model_or_instance, PolymorphicModel):
            model_class = model_or_instance.__class__
            if model_class in strategy_map:
                return strategy_map[model_class]
            else:
                raise serializers.ValidationError("Invalid strategy")

        if isinstance(model_or_instance, str):
            if model_or_instance in [s.value for s in Strategy]:
                return model_or_instance
            else:
                raise serializers.ValidationError("Invalid strategy")
