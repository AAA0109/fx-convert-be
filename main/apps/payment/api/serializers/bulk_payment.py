from rest_framework import serializers

from main.apps.currency.models.currency import Currency
from main.apps.payment.api.serializers.payment import DetailedPaymentRfqResponseSerializer, PaymentSerializer
from main.apps.payment.api.serializers.payment_execution import PaymentExecutionResponseSerializer
from main.apps.payment.services.payment_account import PaymentAccountMethodProvider
from main.apps.payment.services.payment_validator import PaymentValidator


class SimplePaymentSerializer(serializers.Serializer):
    amount = serializers.FloatField(min_value=1)
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all())
    destination = serializers.CharField()
    lock_side = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all())
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    origin = serializers.CharField()
    purpose_of_payment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sell_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all())
    value_date = serializers.DateField()

    def validate(self, attrs:dict):
        attrs = super().validate(attrs)
        try:
            validator = PaymentValidator(attrs=attrs, user=self.context.get('user', None))
            attrs = validator.validate_payload()
        except serializers.ValidationError as e:
            raise e
        return attrs

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        account_method_provider = PaymentAccountMethodProvider(company=self.context.get('user').company,
                                                               payment_payloads=[data],
                                                               is_raw_data=True)
        modified_data = {
            'name': data.get('description', None),
            'origin_account_id': data['origin'],
            'origin_account_method': account_method_provider.get_delivery_method(account_id=data['origin']),
            'destination_account_id': data['destination'],
            'destination_account_method': account_method_provider.get_delivery_method(account_id=data['destination']),
            'amount': data['amount'],
            'buy_currency': data['buy_currency'],
            'delivery_date': data['value_date'],
            'lock_side': data['lock_side'],
            'purpose_of_payment': data.get('purpose_of_payment', None),
            'sell_currency': data['sell_currency'],
        }

        if 'payment_id' in data.keys():
            modified_data['id'] = data['payment_id']
        return modified_data


class SimpleUpdatePaymentSerializer(SimplePaymentSerializer):
    payment_id = serializers.UUIDField(required=False, allow_null=True)


class BulkPaymentRequestSerializer(serializers.Serializer):
    payments = SimplePaymentSerializer(many=True)


class BulkPaymentNettingResult(serializers.Serializer):
    buy_currency = serializers.SlugRelatedField(slug_field='mnemonic', queryset=Currency.objects.all())
    sum_amount = serializers.FloatField()


class BulkPaymentResponseSerializer(serializers.Serializer):
    payments = PaymentSerializer(many=True)
    netting = BulkPaymentNettingResult(many=True)


class BulkPaymentRfqSerializer(serializers.Serializer):
    payment_ids = serializers.ListField(child=serializers.IntegerField())


class BulkDetailedPaymentRfqResponseSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    rfq_status = DetailedPaymentRfqResponseSerializer()


class BulkRfqStatusSerializer(serializers.Serializer):
    rfqs = BulkDetailedPaymentRfqResponseSerializer(many=True)


class BulkPaymentExecutionSerializer(BulkPaymentRfqSerializer):
    pass


class BulkPaymentExecutionResponseSerializer(serializers.Serializer):
    payment_id = serializers.CharField()
    execution_status = PaymentExecutionResponseSerializer()


class BulkExecutionStatusSerializer(serializers.Serializer):
    executions = BulkPaymentExecutionResponseSerializer(many=True)


class BulkPaymentUpdateSerializer(serializers.Serializer):
    payment_group = serializers.CharField()
    added_payments = SimplePaymentSerializer(many=True, required=False)
    updated_payments = SimpleUpdatePaymentSerializer(many=True)
    deleted_payments = serializers.ListField(child=serializers.UUIDField(), required=False)


class BulkPaymentValidationErrorSerializer(serializers.Serializer):
    row_id = serializers.IntegerField()
    is_valid = serializers.BooleanField()
    error_fields = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))


class BulkPaymentValidationErrorResponseSerializer(serializers.Serializer):
    validation_results = BulkPaymentValidationErrorSerializer(many=True)
