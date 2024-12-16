from hdlib.DateTime import Date
from rest_framework import serializers

import logging

from django.db import transaction
from rest_framework import serializers

from main.apps.account.models import Company
from main.apps.corpay.models import Beneficiary, DestinationAccountType
from main.apps.currency.models import FxPair
from rest_framework import serializers

from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
from main.apps.hedge.models.fxforwardposition import FxForwardPosition
from main.apps.hedge.services.forward_cost_service import (
    FxQuoteServiceImpl,
    FxForwardCostCalculatorImpl,
)
from main.apps.margin.services.what_if import DefaultWhatIfMarginInterface
from main.apps.marketdata.services.universe_provider import UniverseProviderService

logger = logging.getLogger(__name__)
universe_provider = UniverseProviderService()
what_if_service = DefaultWhatIfMarginInterface()
fx_quote_service = FxQuoteServiceImpl(universe_provider=universe_provider)


class DraftFxForwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftFxForwardPosition
        fields = [
            'id',
            'status',
            'risk_reduction',
            'fxpair',
            'draft_cashflow',
            'cashflow',
            'installment',
            'origin_account',
            'destination_account',
            'destination_account_type',
            'cash_settle_account',
            'funding_account',
            'is_cash_settle',
            'purpose_of_payment',
            'estimated_fx_forward_price',
            'company'
        ]

    id = serializers.IntegerField(read_only=False, required=False)
    fxpair = serializers.PrimaryKeyRelatedField(required=False, read_only=True)
    origin_account = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    destination_account = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    destination_account_type = serializers.ChoiceField(choices=DestinationAccountType.choices, allow_null=True,
                                                       allow_blank=True, required=False)
    funding_account = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_cash_settle = serializers.BooleanField(default=False)
    cash_settle_account = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.CharField(required=False, read_only=True)
    risk_reduction = serializers.FloatField(required=True)
    purpose_of_payment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    estimated_fx_forward_price = serializers.FloatField(required=False, read_only=True)
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False)

    @transaction.atomic
    def create(self, validated_data):
        date = Date.Date.today()
        spot_cache = universe_provider.fx_spot_provider.get_spot_cache(time=date)

        fwd = DraftFxForwardPosition(
            **validated_data,
            estimated_fx_forward_price=0
        )

        fx_fwd_cost = FxForwardCostCalculatorImpl(fx_quote_servie=fx_quote_service, spot_fx_cache=spot_cache)

        fx_fwd_cost.add_forward(ref_date=date, forward=fwd)
        cost = fx_fwd_cost.costs().get(fwd.company.currency, None)
        if cost is not None:
            fwd.estimated_fx_forward_price = cost.forward_price
            fwd.save()
        return fwd





class FxForwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = FxForwardPosition
        fields = [
            'id',
            'fxpair',
            'amount',
            'delivery_time',
            'enter_time',
            'forward_price',
            'unwind_price',
            'unwind_time'
        ]

    fxpair = serializers.PrimaryKeyRelatedField(read_only=True)


class ActivateDraftFxPositionSerializer(serializers.Serializer):
    funding_account = serializers.CharField(required=False, allow_blank=True, allow_null=True)
