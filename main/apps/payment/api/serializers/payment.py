from rest_framework import serializers
from main.apps.account.models.user import User
from main.apps.approval.api.serializers.approval import ApproverSerializer
from main.apps.approval.services.limit import CompanyLimitService

from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.currency.models.currency import Currency
from main.apps.oems.api.serializers.fields import CurrencyAmountField, CurrencyRateField
from main.apps.oems.models.ticket import Ticket
from main.apps.payment.api.serializers.choices import DELIVERY_METHODS
from main.apps.payment.models.payment import ExecutionOptions, Payment
from main.apps.payment.services.payment_validator import PaymentValidator
from main.apps.settlement.models import Beneficiary


class TicketRateSerializer(serializers.ModelSerializer):
    all_in_cntr_done = CurrencyAmountField(
        coerce_to_string=False, required=False)
    all_in_done = CurrencyAmountField(coerce_to_string=False, required=False)
    all_in_rate = CurrencyRateField(coerce_to_string=False, required=False)
    delivery_fee = CurrencyRateField(coerce_to_string=False, required=False)
    external_quote = CurrencyRateField(coerce_to_string=False, required=False)
    fee = CurrencyRateField(coerce_to_string=False, required=False)
    fwd_points = CurrencyRateField(coerce_to_string=False, required=False)
    quote_fee = CurrencyRateField(coerce_to_string=False, required=False)
    spot_rate = CurrencyRateField(coerce_to_string=False, required=False)

    class Meta:
        model = Ticket
        fields = [
            'ticket_id',
            'side',
            'action',
            'external_quote',
            'quote_fee',
            'fee',
            'delivery_fee',
            'delivery_fee_unit',
            'all_in_done',
            'all_in_cntr_done',
            'all_in_rate',
            'spot_rate',
            'fwd_points',
            'transaction_time',
        ]


class SingleCashflowSerializer(serializers.ModelSerializer):
    amount = CurrencyAmountField(coerce_to_string=False)
    buy_currency = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all())
    cntr_amount = CurrencyAmountField(coerce_to_string=False, required=False)
    lock_side = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all())
    sell_currency = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all())
    ticket = TicketRateSerializer(
        source='related_ticket', read_only=True, required=False)

    class Meta:
        model = SingleCashFlow
        fields = [
            'cashflow_id',
            'amount',
            'buy_currency',
            'cntr_amount',
            'description',
            'lock_side',
            'name',
            'pay_date',
            'sell_currency',
            'created',
            'modified',
            'ticket',
            'transaction_date',
        ]

        read_only_fields = [
            'transaction_date',
        ]


class PaymentInstallmentSerializer(serializers.Serializer):
    amount = CurrencyAmountField(coerce_to_string=False)
    cntr_amount = CurrencyAmountField(coerce_to_string=False, required=False)
    buy_currency = serializers.CharField()
    date = serializers.DateField()
    cashflow_id = serializers.CharField(required=False)
    lock_side = serializers.CharField()
    sell_currency = serializers.CharField()


class PaymentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    amount = CurrencyAmountField(
        source='cashflow_generator.amount', required=False, min_value=0, coerce_to_string=False)
    cntr_amount = CurrencyAmountField(
        source='cashflow_generator.cntr_amount', required=False, min_value=0, coerce_to_string=False)
    buy_currency = serializers.CharField(
        source='cashflow_generator.buy_currency.mnemonic', required=False)
    cashflows = SingleCashflowSerializer(
        many=True, source='cashflow_generator.cashflows', read_only=True)
    delivery_date = serializers.DateField(
        source='cashflow_generator.value_date', required=False, allow_null=True)
    installment = serializers.BooleanField(
        source='cashflow_generator.installment', read_only=True)
    installments = PaymentInstallmentSerializer(
        many=True, write_only=True, required=False, allow_null=True)
    lock_side = serializers.CharField(
        source='cashflow_generator.lock_side.mnemonic', required=False)
    name = serializers.CharField(source='cashflow_generator.name')
    periodicity = serializers.CharField(
        source='cashflow_generator.periodicity', required=False, allow_null=True, allow_blank=True)
    periodicity_end_date = serializers.DateField(source='cashflow_generator.periodicity_end_date', required=False,
                                                 allow_null=True)
    periodicity_start_date = serializers.DateField(source='cashflow_generator.periodicity_start_date', required=False,
                                                   allow_null=True)
    purpose_of_payment = serializers.ChoiceField(
        choices=Beneficiary.Purpose, required=False, allow_blank=True, allow_null=True)
    recurring = serializers.BooleanField(
        source='cashflow_generator.recurring', read_only=True)
    sell_currency = serializers.CharField(
        source='cashflow_generator.sell_currency.mnemonic', required=False)
    origin_account_method = serializers.ChoiceField(
        choices=DELIVERY_METHODS, required=False, allow_null=True)
    destination_account_method = serializers.ChoiceField(
        choices=DELIVERY_METHODS, required=False, allow_null=True)
    fee = CurrencyRateField(coerce_to_string=False, required=False)
    approvers = ApproverSerializer(many=True, required=False, allow_null=True)
    min_approvers = serializers.IntegerField(required=False, allow_null=True)
    assigned_approvers = ApproverSerializer(many=True, required=False, allow_null=True)
    execution_timing = serializers.ChoiceField(
        choices=ExecutionOptions.choices, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Payment
        fields = [
            'amount',
            'cntr_amount',
            'buy_currency',
            'cashflows',
            'created',
            'delivery_date',
            'destination_account_id',
            'destination_account_method',
            'execution_timing',
            'fee_in_bps',
            'fee',
            'id',
            'installment',
            'installments',
            'lock_side',
            'modified',
            'name',
            'origin_account_id',
            'origin_account_method',
            'payment_status',
            'periodicity_end_date',
            'periodicity_start_date',
            'periodicity',
            'purpose_of_payment',
            'recurring',
            'sell_currency',
            'payment_id',
            'payment_group',
            'approvers',
            'min_approvers',
            'assigned_approvers'
        ]

        read_only_fields = [
            'created',
            'id',
            'modified',
            'payment_status',
            'payment_group',
            'approvers',
            'min_approvers',
            'assigned_approvers'
        ]

        def validate_amount(self, value):
            if value == 0:
                raise serializers.ValidationError({
                    'amount': 'Payment amount cannot be zero'
                })
            return value

    def to_internal_value(self, data):
        payload = super().to_internal_value(data)
        for key in payload['cashflow_generator'].keys():
            if 'currency' in key or key == 'lock_side':
                payload[key] = payload['cashflow_generator'][key]['mnemonic']
                continue
            elif 'periodicity' in key:
                payload[key] = payload['cashflow_generator'][key]
                continue
            payload[key.replace('value_date', 'delivery_date')
                    ] = payload['cashflow_generator'][key]
        payload.pop('cashflow_generator')
        return payload

    def validate(self, attrs: dict):
        attrs = super().validate(attrs)
        limit_svc = CompanyLimitService(company=self.initial_data['user'].company)
        amount = None
        value_date = None
        if 'installments' in attrs and len(attrs['installments']) > 0:
            installment = attrs['installments'][0]
            value_date = installment['date']
            amount = installment['amount']
        elif 'periodicity' in attrs:
            value_date = attrs['periodicity_start_date']
            amount = attrs['amount']
        else:
            value_date = attrs['delivery_date']
            amount = attrs['amount']

        if amount is not None and value_date is not None:
            converted_amount, is_exceeding_limit = \
                limit_svc.validate_transaction_limit(currency=attrs['lock_side'],
                                                    amount=amount,
                                                    value_date=value_date)
            if is_exceeding_limit:
                raise serializers.ValidationError({
                        'amount': 'Amount is exceeding company limit'
                    })

            is_exceeding_tenor = limit_svc.is_tenor_exceeding_limit(value_date=value_date)
            if is_exceeding_tenor:
                raise serializers.ValidationError({
                        'value_date': 'value date is exceeding company tenor limit'
                    })

        try:
            validator = PaymentValidator(
                attrs=attrs, user=self.initial_data['user'])
            attrs = validator.validate_payload()
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise e
        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['execution_timing'] = instance.execution_option
        default_amount = representation['amount']
        default_cntr_amount = representation['cntr_amount']
        representation['amount'] = 0
        representation['cntr_amount'] = 0
        for cashflow in representation['cashflows']:
            if "ticket" not in cashflow:
                continue
            ticket = cashflow['ticket']
            if ticket is None:
                continue

            # pick sides based on trade side
            if ticket['side'] == Ticket.Sides.SELL:
                all_in_cost = ticket['all_in_done']
                payment_amount = ticket['all_in_cntr_done']
            else:
                all_in_cost = ticket['all_in_cntr_done']
                payment_amount = ticket['all_in_done']

            # assign based on lock side
            if representation['buy_currency'] == representation['lock_side']:
                representation['amount'] += payment_amount
                representation['cntr_amount'] += all_in_cost
            else:
                representation['amount'] += all_in_cost
                representation['cntr_amount'] += payment_amount

        if not default_amount is None and representation['amount'] == 0 and default_amount > 0:
            representation['amount'] = default_amount
        if not default_cntr_amount is None and representation['cntr_amount'] == 0 and default_cntr_amount > 0:
            representation['cntr_amount'] = default_cntr_amount

        return representation


class InstallmentCashflowSerializer(SingleCashflowSerializer):
    class Meta:
        model = SingleCashFlow
        exclude = ['id', 'generator', 'company', 'tickets']
        read_only_fields = [
            'created',
            'description',
            'id',
            'modified',
            'name',
            'status'
        ]


class PaymentRfqSerializer(serializers.ModelSerializer):
    sell_currency = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all())
    buy_currency = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all())
    lock_side = serializers.SlugRelatedField(
        slug_field='mnemonic', queryset=Currency.objects.all())
    transaction_amount = CurrencyAmountField(
        read_only=True, coerce_to_string=False)
    delivery_fee = CurrencyAmountField(read_only=True, coerce_to_string=False)
    total_cost = CurrencyAmountField(read_only=True, coerce_to_string=False)
    indicative = serializers.BooleanField(read_only=True)
    pangea_fee = serializers.CharField(required=False)
    broker_fee = serializers.CharField(required=False)
    forward_points_str = serializers.CharField(required=False)

    class Meta:
        model = Ticket
        fields = [
            'amount',
            'buy_currency',
            'cashflow_id',
            'external_quote_expiry',
            'external_quote',
            'fee',
            'fwd_points',
            'lock_side',
            'quote_fee',
            'sell_currency',
            'spot_rate',
            'ticket_id',
            'value_date',
            'transaction_amount',
            'delivery_fee',
            'total_cost',
            'indicative',
            'pangea_fee',
            'broker_fee',
            'forward_points_str'
        ]


class FailedPaymentRfqSerializer(serializers.Serializer):
    cashflow_id = serializers.CharField(required=False)
    ticket_id = serializers.CharField(required=False)
    status = serializers.CharField()
    message = serializers.CharField()
    code = serializers.IntegerField()
    data = serializers.DictField(child=serializers.CharField(
        required=False, allow_null=True), required=False, allow_null=True)


class DetailedPaymentRfqResponseSerializer(serializers.Serializer):
    success = PaymentRfqSerializer(many=True)
    failed = FailedPaymentRfqSerializer(many=True, required=False)


class PaymentErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
    traceback = serializers.CharField(required=False)


class PaymentValidationErrorDetailSerializer(serializers.Serializer):
    field = serializers.CharField(required=False, allow_blank=True)
    detail = serializers.CharField(required=False, allow_blank=True)


class PaymentValidationErrorSerializer(PaymentErrorSerializer):
    error = None
    validation_errors = PaymentValidationErrorDetailSerializer(many=True)

