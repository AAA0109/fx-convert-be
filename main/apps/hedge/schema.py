import graphene
from graphene_django import DjangoObjectType

from main.apps.hedge.models.hedgesettings import HedgeSettings

class HedgeSettingsNode(DjangoObjectType):
    class Meta:
        model = HedgeSettings
        fields = ("id", "account", "max_horizon_days", "margin_budget", "method", "custom", "updated")
