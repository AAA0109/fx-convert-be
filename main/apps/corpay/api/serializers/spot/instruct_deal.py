from rest_framework import serializers

from main.apps.corpay.api.serializers.base import LinkSerializer
from main.apps.corpay.api.serializers.choices import DELIVERY_METHODS


class InstructDealRequestOrderSerializer(serializers.Serializer):
    order_id = serializers.CharField(required=False)
    amount = serializers.FloatField()


class InstructDealRequestPaymentSerializer(serializers.Serializer):
    beneficiary_id = serializers.CharField()
    delivery_method = serializers.ChoiceField(choices=DELIVERY_METHODS)
    amount = serializers.FloatField()
    currency = serializers.CharField()
    purpose_of_payment = serializers.CharField()
    payment_reference = serializers.CharField(required=False, allow_blank=True)


class InstructDealRequestSettlementSerializer(serializers.Serializer):
    account_id = serializers.CharField()
    delivery_method = serializers.ChoiceField(choices=DELIVERY_METHODS)
    currency = serializers.CharField()
    SETTLEMENT_PURPOSES = (
        ('All', 'All'),
        ('Allocation', 'Allocation'),
        ('Fee', 'Fee'),
        ('Spot', 'Spot'),
        ('SpotTrade', 'SpotTrade'),
        ('Drawdown', 'Drawdown')
    )
    purpose = serializers.ChoiceField(choices=SETTLEMENT_PURPOSES)


class InstructDealRequestSerializer(serializers.Serializer):
    orders = InstructDealRequestOrderSerializer(many=True)
    payments = InstructDealRequestPaymentSerializer(many=True)
    settlements = InstructDealRequestSettlementSerializer(many=True)


class InstructDealResponsePaymentSerializer(serializers.Serializer):
    payment_instruction_id = serializers.IntegerField(source='paymentInstructionId')
    available_date = serializers.DateTimeField(source='availableDate')
    order_id = serializers.CharField(allow_null=True, source='orderId')
    amount = serializers.FloatField()
    currency = serializers.CharField()
    approval_status = serializers.CharField(source='approvalStatus')
    fee_amount = serializers.FloatField(source='feeAmount')
    fee_currency = serializers.CharField(source='feeCurrency')
    estimate_cost_amount = serializers.FloatField(source='estimateCostAmount')
    estimate_cost_currency = serializers.CharField(source='estimateCostCurrency')
    bene_id = serializers.CharField(source='beneId')
    reference = serializers.CharField()
    method = serializers.CharField()
    payee_name = serializers.CharField(source='payeeName')
    account_type = serializers.CharField(source='accountType')
    payee_account = serializers.CharField(allow_null=True)
    client_integration_id = serializers.CharField(source='clientIntegrationId')
    tracker_id = serializers.CharField(source='trackerId')
    links = LinkSerializer(many=True)


class InstructDealResponseSettlementSerializer(serializers.Serializer):
    account_id = serializers.CharField(source='accountId')
    method = serializers.CharField()
    method_description = serializers.CharField(source='methodDescription')
    account_details = serializers.CharField(source='accountDetails')
    payment_ident = serializers.CharField(source='paymentIdent')
    settlement_id = serializers.CharField(source='settlementId')
    is_fee = serializers.BooleanField(source='isFee')
    amount = serializers.FloatField()
    currency = serializers.CharField()
    account_type = serializers.CharField(source='accountType')
    links = LinkSerializer(many=True)


class InstructDealResponseOrderDetailSerializer(serializers.Serializer):
    entry_date = serializers.DateTimeField(source="entryDate")
    ord_num = serializers.CharField(source='ordNum')
    buy = serializers.CharField()
    buy_amount = serializers.FloatField(source='buyAmount')
    sell = serializers.CharField()
    sell_amount = serializers.FloatField(source='sellAmount')
    exchange = serializers.FloatField()
    our_action = serializers.CharField(source='ourAction')
    token = serializers.CharField()


class InstructDealResponseSerializer(serializers.Serializer):
    ord_num = serializers.CharField(source="ordNum")
    value_date = serializers.DateTimeField(source="valueDate")
    new_payment_ids = serializers.ListField(child=serializers.IntegerField(), source='newPaymentIds')
    payments = InstructDealResponsePaymentSerializer(many=True)
    settlements = InstructDealResponseSettlementSerializer(many=True)
    order_detail = InstructDealResponseOrderDetailSerializer(source="orderDetail")
    enable_approve_trade_button = serializers.BooleanField(source='enableApproveTradeButton')
    show_approve_trade_button = serializers.BooleanField(source='showApproveTradeButton')
