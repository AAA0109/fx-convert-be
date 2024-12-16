from hdlib.DateTime.Date import Date
from rest_framework import serializers

from main.apps.core.serializers.common import HDLDateField
from main.apps.hedge.serializers.models.hedgesettings import HedgeSettingsSerializer


class MarginRequirementSerializer(serializers.Serializer):
    """
    An object representing the margin requirement for a given date.
    """
    date = HDLDateField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, label="The margin amount")
    health_score = serializers.FloatField()
    health_score_after_deposit = serializers.FloatField()
    health_score_hypothetical = serializers.FloatField()
    total_hedging = serializers.DecimalField(max_digits=20, decimal_places=2)


class DepositSerializer(serializers.Serializer):
    date = HDLDateField()
    amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    currency = serializers.CharField()


class MarginHealthResponse(serializers.Serializer):
    """
    Margin health response object.

    It represents the margin health over the next 30 days.
    """
    margin_balance = serializers.FloatField()

    recommended_deposit = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)
    recommended_withdrawl = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)
    minimum_deposit = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)
    maximum_withdrawl = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)

    margins = serializers.ListField(child=MarginRequirementSerializer())
    ach_deposit_date = HDLDateField()
    wire_deposit_date = HDLDateField()

    deposit_history = serializers.ListField(child=DepositSerializer())


class MarginHealthRequest(serializers.Serializer):
    """
    A request to calculate the margin health for a company.

    If the custom_amount us provided, it will be used to calculate the margin health. Otherwise, the margin health will
     be calculated for the recommended amount.
    """

    custom_amount = serializers.FloatField(required=False)


class MarginAndFeeRequest(serializers.Serializer):
    """
    Margin and fee request object.

    If the draft is associated with a live cashflow then this is an edit of an existing cashflow and the account id
    will be ignored.

    If on the other hand the draft is not associated with a live cashflow then the account id must be specified.
    """
    draft_ids = serializers.ListSerializer(required=False, child=serializers.IntegerField())
    deleted_cashflow_ids = serializers.ListSerializer(required=False, child=serializers.IntegerField())
    account_id = serializers.IntegerField(required=False)
    hedge_settings = HedgeSettingsSerializer(required=False)


class FeeDetailSerializer(serializers.Serializer):
    """
    Fee detail serializer.

    This is the fee detail with the cost of hedging a specific cashflow.
    """
    update_fee_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    update_fee_percentage = serializers.DecimalField(max_digits=20, decimal_places=2)

    hold_fee_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    hold_fee_percentage = serializers.DecimalField(max_digits=20, decimal_places=2)

    cashflow_update_fee_at_close_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    cashflow_update_fee_at_close_percent = serializers.DecimalField(max_digits=20, decimal_places=2)

    max_hedge_cost = serializers.DecimalField(max_digits=20, decimal_places=2)

    roll_cost_amount = serializers.DecimalField(max_digits=20, decimal_places=2)

    roll_cost_percentage = serializers.DecimalField(max_digits=20, decimal_places=2)


class FeeSerializer(serializers.Serializer):
    name = serializers.CharField()
    amount = serializers.FloatField()
    rate = serializers.FloatField()


class FeeTotalSerializer(FeeSerializer):
    pass


class FeeGroupsSerializer(serializers.Serializer):
    name = serializers.CharField()
    fees = serializers.ListSerializer(child=FeeSerializer())


class FeeDetailsSerializer(serializers.Serializer):
    totals = FeeTotalSerializer()
    fee_groups = serializers.ListSerializer(child=FeeGroupsSerializer())


class MarginAndFeesResponse(serializers.Serializer):
    """
    Margin and fees response object.
    """
    margin_required = serializers.DecimalField(max_digits=20, decimal_places=2)
    margin_available = serializers.DecimalField(max_digits=20, decimal_places=2)
    cashflow_total_value = serializers.DecimalField(max_digits=20, decimal_places=2)
    last_maturity_days = serializers.DecimalField(max_digits=20, decimal_places=2)
    num_cashflows = serializers.IntegerField()
    previous_daily_aum = serializers.DecimalField(max_digits=20, decimal_places=2)
    previous_rolling_aum = serializers.DecimalField(max_digits=20, decimal_places=2)

    fee_detail = FeeDetailSerializer()
    fee_details = FeeDetailsSerializer()
