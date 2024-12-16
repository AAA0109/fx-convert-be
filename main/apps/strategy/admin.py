from django.contrib import admin
from polymorphic.admin import PolymorphicChildModelAdmin, PolymorphicParentModelAdmin, PolymorphicChildModelFilter

from main.apps.strategy.models import HedgingStrategy, AutopilotHedgingStrategy, ParachuteHedgingStrategy, \
    ZeroGravityHedgingStrategy, SelfDirectedHedgingStrategy


# Register your models here.


class HedgingStrategyChildAdmin(PolymorphicChildModelAdmin):
    base_model = HedgingStrategy


@admin.register(AutopilotHedgingStrategy)
class AutopilotHedgingStrategyAdmin(HedgingStrategyChildAdmin):
    base_model = AutopilotHedgingStrategy


@admin.register(ParachuteHedgingStrategy)
class ParachuteHedgingStrategyAdmin(HedgingStrategyChildAdmin):
    base_model = ParachuteHedgingStrategy


@admin.register(ZeroGravityHedgingStrategy)
class ZeroGravityHedgingStrategyAdmin(HedgingStrategyChildAdmin):
    base_model = ZeroGravityHedgingStrategy


@admin.register(SelfDirectedHedgingStrategy)
class SelfGuidedHedgingStrategyAdmin(HedgingStrategyChildAdmin):
    base_model = SelfDirectedHedgingStrategy


@admin.register(HedgingStrategy)
class HedgingStrategyAdmin(PolymorphicParentModelAdmin):
    base_model = HedgingStrategy
    child_models = (
        AutopilotHedgingStrategy,
        ParachuteHedgingStrategy,
        ZeroGravityHedgingStrategy,
        SelfDirectedHedgingStrategy
    )
    list_filter = (PolymorphicChildModelFilter,)
