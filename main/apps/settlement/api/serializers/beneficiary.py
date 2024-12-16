from django.db.models import Prefetch
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from main.apps.broker.api.serializers.broker import BrokerSerializer
from main.apps.core.constants import CURRENCY_HELP_TEXT, COUNTRY_HELP_TEXT, ADDITIONAL_FIELDS_HELP_TEXT, \
    REGULATORY_HELP_TEXT, PHONE_HELP_TEXT
from main.apps.corpay.api.serializers.choices import BENEFICIARY_CLASSIFICATIONS, BENEFICIARY_PAYMENT_METHODS
from main.apps.currency.models import Currency
from main.apps.settlement.models import Beneficiary, BeneficiaryBroker


class BeneficiarySerializer(serializers.ModelSerializer):
    beneficiary_phone = PhoneNumberField(
        help_text=PHONE_HELP_TEXT
    )
    payment_methods = serializers.MultipleChoiceField(
        choices=Beneficiary.PaymentSettlementMethod.choices,
        help_text="Payment methods"
    )
    settlement_methods = serializers.MultipleChoiceField(
        choices=Beneficiary.PaymentSettlementMethod.choices,
        help_text="Settlement methods"
    )
    destination_currency = serializers.SlugRelatedField(
        slug_field='mnemonic',
        queryset=Currency.objects.all(),
        help_text=CURRENCY_HELP_TEXT
    )
    additional_fields = serializers.JSONField(
        help_text=ADDITIONAL_FIELDS_HELP_TEXT,
        required=False,
        allow_null=True
    )
    regulatory = serializers.JSONField(
        help_text=REGULATORY_HELP_TEXT,
        required=False,
        allow_null=True
    )
    brokers = BrokerSerializer(many=True, read_only=True)

    class Meta:
        model = Beneficiary
        fields = (
            'beneficiary_id',
            'beneficiary_account_type',
            'destination_country',
            'destination_currency',
            'payment_methods',
            'settlement_methods',
            'preferred_method',
            'payment_reference',
            'beneficiary_account_type',
            'beneficiary_name',
            'beneficiary_alias',
            'beneficiary_address_1',
            'beneficiary_address_2',
            'beneficiary_country',
            'beneficiary_region',
            'beneficiary_postal',
            'beneficiary_city',
            'beneficiary_phone',
            'beneficiary_email',
            'classification',
            'date_of_birth',
            'identification_type',
            'identification_value',
            'bank_account_type',
            'bank_code',
            'bank_account_number',
            'bank_account_number_type',
            'bank_name',
            'bank_country',
            'bank_region',
            'bank_city',
            'bank_postal',
            'bank_address_1',
            'bank_address_2',
            'bank_branch_name',
            'bank_instruction',
            'bank_routing_code_value_1',
            'bank_routing_code_type_1',
            'bank_routing_code_value_2',
            'bank_routing_code_type_2',
            'bank_routing_code_value_3',
            'bank_routing_code_type_3',
            'inter_bank_account_type',
            'inter_bank_code',
            'inter_bank_account_number',
            'inter_bank_account_number_type',
            'inter_bank_name',
            'inter_bank_country',
            'inter_bank_region',
            'inter_bank_city',
            'inter_bank_postal',
            'inter_bank_address_1',
            'inter_bank_address_2',
            'inter_bank_branch_name',
            'inter_bank_instruction',
            'inter_bank_routing_code_value_1',
            'inter_bank_routing_code_type_1',
            'inter_bank_routing_code_value_2',
            'inter_bank_routing_code_type_2',
            'client_legal_entity',
            'default_purpose',
            'default_purpose_description',
            'proxy_type',
            'proxy_value',
            'further_name',
            'further_account_number',
            'status',
            'additional_fields',
            "regulatory",
            "brokers"
        )
        read_only_fields = ['status', 'beneficiary_id', 'created', 'modified']

    def validate(self, data):
        beneficiary_alias = data.get('beneficiary_alias')
        company = data.get('company') or (self.instance.company if self.instance else None)

        if beneficiary_alias and company:
            existing_beneficiary = Beneficiary.objects.filter(
                company=company,
                beneficiary_alias=beneficiary_alias
            ).exclude(pk=self.instance.pk if self.instance else None).first()

            if existing_beneficiary:
                raise serializers.ValidationError({
                    "beneficiary_alias": "A beneficiary with this alias already exists in this company."
                })

        return data

    def to_representation(self, instance):
       try:
           # Ensure the instance is prefetched
           if not hasattr(instance,
                          '_prefetched_objects_cache') or 'beneficiarybroker_set' not in instance._prefetched_objects_cache:
               instance = self.Meta.model.objects.prefetch_related(
                   Prefetch('beneficiarybroker_set', queryset=BeneficiaryBroker.objects.select_related('broker'))
               ).get(pk=instance.pk)
           # Now we can safely serialize
           representation = super().to_representation(instance)
           representation['brokers'] = BrokerSerializer(
               [bb.broker for bb in instance.beneficiarybroker_set.all()],
               many=True
           ).data
       except Beneficiary.DoesNotExist:
           representation = super().to_representation(instance)
       return representation

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance:Beneficiary, validated_data):
        instance = super().update(instance, validated_data)
        instance.status = Beneficiary.Status.PENDING
        instance.save()

        from main.apps.settlement.tasks import sync_beneficiary_to_brokers

        sync_beneficiary_to_brokers(instance.pk)

        return instance


class ActivateBeneficiaryRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True,
                                       help_text="This can be either be beneficiary_id or alias")


class ValidationSchemaRequestSerializer(serializers.Serializer):
    destination_country = serializers.CharField(required=True, help_text=COUNTRY_HELP_TEXT)
    bank_country = serializers.CharField(required=True, help_text=COUNTRY_HELP_TEXT)
    bank_currency = serializers.CharField(required=True, help_text=CURRENCY_HELP_TEXT)
    beneficiary_account_type = serializers.ChoiceField(required=True, choices=Beneficiary.AccountType.choices)
    payment_method = serializers.ChoiceField(required=False, choices=Beneficiary.PaymentSettlementMethod.choices)
