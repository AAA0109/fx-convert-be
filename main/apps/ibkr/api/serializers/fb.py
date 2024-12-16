from rest_framework import serializers

from main.apps.currency.api.serializers.models.currency import CurrencySerializer
from main.apps.ibkr.models import FundingRequest, FundingRequestStatus, DepositResult, \
    FundingRequestProcessingStat, WireInstruction, WithdrawResult


class FundingRequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingRequestStatus
        exclude = ('details',)


class FundingRequestProcessingStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingRequestProcessingStat
        fields = '__all__'


class DepositResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositResult
        fields = '__all__'


class WithdrawResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawResult
        fields = '__all__'


class FundingRequestSerializer(serializers.ModelSerializer):
    status = FundingRequestStatusSerializer()
    deposit_result = DepositResultSerializer(required=False)
    withdraw_result = WithdrawResultSerializer(required=False)

    class Meta:
        model = FundingRequest
        fields = '__all__'


class DepositRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    broker_account_id = serializers.IntegerField()
    CURRENCIES = [
        ('USD', 'USD'),
        ('HUF', 'HUF'),
        ('EUR', 'EUR'),
        ('CZK', 'CZK'),
        ('GBP', 'GBP'),
        ('CNH', 'CNH'),
        ('CAD', 'CAD'),
        ('DKK', 'DKK'),
        ('JPY', 'JPY'),
        ('RUB', 'RUB'),
        ('HKD', 'HKD'),
        ('ILS', 'ILS'),
        ('AUD', 'AUD'),
        ('NOK', 'NOK'),
        ('CHF', 'CHF'),
        ('SGD', 'SGD'),
        ('MXN', 'MXN'),
        ('PLN', 'PLN'),
        ('SEK', 'SEK'),
        ('ZAR', 'ZAR'),
        ('NZD', 'NZD'),
    ]
    currency = serializers.ChoiceField(choices=CURRENCIES)
    METHODS = [
        ('ACH', 'ACH'),
        ('ACHUS', 'ACHUS'),
        ('ACHCA', 'ACHCA'),
        ('WIRE', 'WIRE'),
    ]
    method = serializers.ChoiceField(choices=METHODS, default='WIRE')
    saved_instruction_name = serializers.CharField(required=False)

class WithdrawRequestSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    broker_account_id = serializers.IntegerField()
    METHODS = [
        ('ACH', 'ACH'),
        ('ACHUS', 'ACHUS'),
        ('ACHCA', 'ACHCA'),
        ('WIRE', 'WIRE'),
    ]
    method = serializers.ChoiceField(choices=METHODS, default='WIRE')
    CURRENCIES = [
        ('USD', 'USD'),
        ('HUF', 'HUF'),
        ('EUR', 'EUR'),
        ('CZK', 'CZK'),
        ('GBP', 'GBP'),
        ('CNH', 'CNH'),
        ('CAD', 'CAD'),
        ('DKK', 'DKK'),
        ('JPY', 'JPY'),
        ('RUB', 'RUB'),
        ('HKD', 'HKD'),
        ('ILS', 'ILS'),
        ('AUD', 'AUD'),
        ('NOK', 'NOK'),
        ('CHF', 'CHF'),
        ('SGD', 'SGD'),
        ('MXN', 'MXN'),
        ('PLN', 'PLN'),
        ('SEK', 'SEK'),
        ('ZAR', 'ZAR'),
        ('NZD', 'NZD')
    ]
    currency = serializers.ChoiceField(choices=CURRENCIES, default='USD')
    saved_instruction_name = serializers.CharField(max_length=250)
    date_time_to_occur = serializers.DateTimeField()

class IBFBResponseSerializer(serializers.Serializer):
    funding_request = FundingRequestSerializer()


class GetInstructionNameRequestSerializer(serializers.Serializer):
    broker_account_id = serializers.IntegerField()
    METHODS = [
        ('CAACH', 'CAACH'),
        ('ACHUS', 'ACHUS'),
        ('ACHCA', 'ACHCA'),
        ('WIRE', 'WIRE')
    ]
    method = serializers.ChoiceField(choices=METHODS, default='ACHUS')


class GetStatusSerializer(serializers.Serializer):
    funding_request_id = serializers.IntegerField()


class ListFundingRequestsSerializer(serializers.Serializer):
    broker_account_id = serializers.IntegerField()
    METHODS = [
        ('deposit_funds', 'deposit_funds'),
        ('instruction_name', 'instruction_names')
    ]
    method = serializers.ChoiceField(choices=METHODS, required=False)


class ListWireInstructionsSerializers(serializers.Serializer):
    mnemonic = serializers.CharField(max_length=3)


class WireInstructionSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer()

    class Meta:
        model = WireInstruction
        fields = '__all__'


class FinancialInstitutionSerializer(serializers.Serializer):
    IDENTIFIER_TYPE = [
        ('IFSC', 'IFSC')
    ]
    name = serializers.CharField(max_length=60)
    identifier = serializers.CharField(max_length=60)
    identifier_type = serializers.ChoiceField(choices=IDENTIFIER_TYPE)


class PredefinedDestinationInstructionRequest(serializers.Serializer):
    broker_account_id = serializers.IntegerField()
    INSTRUCTION_TYPE = [
        ('WIRE', 'WIRE'),
        ('ACH', 'ACH')
    ]
    CURRENCIES = [
        ('USD', 'USD'),
        ('HUF', 'HUF'),
        ('EUR', 'EUR'),
        ('CZK', 'CZK'),
        ('GBP', 'GBP'),
        ('CNH', 'CNH'),
        ('CAD', 'CAD'),
        ('DKK', 'DKK'),
        ('JPY', 'JPY'),
        ('RUB', 'RUB'),
        ('HKD', 'HKD'),
        ('ILS', 'ILS'),
        ('AUD', 'AUD'),
        ('NOK', 'NOK'),
        ('CHF', 'CHF'),
        ('SGD', 'SGD'),
        ('MXN', 'MXN'),
        ('PLN', 'PLN'),
        ('SEK', 'SEK'),
        ('ZAR', 'ZAR'),
        ('NZD', 'NZD'),
    ]
    instruction_name = serializers.CharField(max_length=60)
    instruction_type = serializers.ChoiceField(choices=INSTRUCTION_TYPE)
    financial_institution = FinancialInstitutionSerializer()
    financial_institution_client_acct_id = serializers.CharField(max_length=250)
    currency = serializers.ChoiceField(choices=CURRENCIES)
