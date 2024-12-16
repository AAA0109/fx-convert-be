from rest_framework import serializers

from main.apps.corpay.api.serializers.base import LinkSerializer, SortingSerializer, ValueSetSerializer, \
    ListDataSerializer, FacetSerializer, MessageSerializer, KeyValueSerializer
from main.apps.corpay.api.serializers.choices import BENEFICIARY_CLASSIFICATIONS, BENEFICIARY_PAYMENT_METHODS, \
    BENEFICIARY_STATUSES
from main.apps.corpay.api.serializers.base import PaginationSerializer


class BeneficiaryRulesRequestSerializer(serializers.Serializer):
    destination_country = serializers.CharField(required=False)
    bank_country = serializers.CharField(required=False)
    bank_currency = serializers.CharField(required=False)
    rules_classification = serializers.ChoiceField(choices=BENEFICIARY_CLASSIFICATIONS, required=False)
    payment_method = serializers.ChoiceField(choices=BENEFICIARY_PAYMENT_METHODS, required=False)


class RuleSerializer(serializers.Serializer):
    id = serializers.CharField()
    regex = serializers.CharField(source='regEx')
    is_required = serializers.BooleanField(source='isRequired')
    error_message = serializers.CharField(source='errorMessage', required=False)
    is_required_in_value_set = serializers.BooleanField(source='isRequiredInValueSet')
    value_set = ValueSetSerializer(many=True, source='valueSet', required=False)


class BeneficiaryRuleSerializer(RuleSerializer):
    links = LinkSerializer(many=True, required=False)


class BeneficiaryRegulatoryRuleSerializer(RuleSerializer):
    order = serializers.IntegerField()
    label = serializers.CharField()


class BeneficiaryRulesTemplateGuideSerializer(serializers.Serializer):
    rules = BeneficiaryRuleSerializer(many=True)
    regulatory_rules = BeneficiaryRegulatoryRuleSerializer(many=True, source='regulatoryRules')
    provide = serializers.ListSerializer(child=serializers.CharField())


class BeneficiaryRulesResponseSerializer(serializers.Serializer):
    template_guide = BeneficiaryRulesTemplateGuideSerializer(source='templateGuide')

    def to_representation(self, instance):
        saved_links = {}
        if instance['templateGuide']['rules'] is not None:
            for rule in instance['templateGuide']['rules']:
                if 'links' in rule:
                    for link in rule['links']:
                        if link['rel'] == 'COUNTRIES':
                            saved_links['countries'] = link
                        if link['rel'] == 'REGIONS':
                            saved_links['regions'] = link
            for rule in instance['templateGuide']['rules']:
                if 'Country' in rule['id'] and 'links' not in rule:
                    rule['links'] = [
                        saved_links['countries']
                    ]
                if 'Region' in rule['id'] and 'links' not in rule:
                    rule['links'] = [
                        saved_links['regions']
                    ]
        return super().to_representation(instance)


class BeneficiaryRequestSerializer(serializers.Serializer):
    account_holder_name = serializers.CharField()
    template_identifier = serializers.CharField(required=False, allow_blank=True)
    destination_country = serializers.CharField()
    bank_currency = serializers.CharField()
    classification = serializers.CharField()
    payment_methods = serializers.MultipleChoiceField(choices=BENEFICIARY_PAYMENT_METHODS)
    preferred_method = serializers.CharField()
    account_number = serializers.CharField()
    local_account_number = serializers.CharField(required=False, allow_blank=True)
    routing_code = serializers.CharField(required=False, allow_blank=True)
    local_routing_code = serializers.CharField(required=False, allow_blank=True)
    account_holder_country = serializers.CharField()
    account_holder_region = serializers.CharField(required=False, allow_blank=True)
    account_holder_address1 = serializers.CharField()
    account_holder_address2 = serializers.CharField(required=False, allow_blank=True)
    account_holder_city = serializers.CharField()
    account_holder_postal = serializers.CharField(required=False, allow_blank=True)
    account_holder_phone_number = serializers.CharField(required=False, allow_blank=True)
    account_holder_email = serializers.EmailField(required=False, allow_blank=True)
    send_pay_tracker = serializers.BooleanField(required=False)
    iban = serializers.CharField(required=False, allow_blank=True)
    swift_bic_code = serializers.CharField()
    bank_name = serializers.CharField()
    bank_country = serializers.CharField()
    bank_region = serializers.CharField(required=False, allow_blank=True)
    bank_city = serializers.CharField()
    bank_address_line1 = serializers.CharField()
    bank_address_line2 = serializers.CharField(required=False, allow_blank=True)
    bank_postal = serializers.CharField(required=False, allow_blank=True)
    payment_reference = serializers.CharField(required=False, allow_blank=True)
    purpose_of_payment = serializers.CharField(required=False, allow_blank=True)
    internal_payment_alert = serializers.CharField(required=False, allow_blank=True)
    external_payment_alert = serializers.CharField(required=False, allow_blank=True)
    method_of_delivery = serializers.CharField(required=False, allow_blank=True)
    regulatory = KeyValueSerializer(many=True)
    is_withdraw = serializers.BooleanField(default=False)


class BeneficiaryResponseSerializer(serializers.Serializer):
    template_id = serializers.CharField(source='templateId')
    client_integration_id = serializers.CharField()


class DeleteBeneficiaryRequestSerializer(serializers.Serializer):
    client_integration_id = serializers.CharField()


class BeneMethodSerializer(serializers.Serializer):
    method = serializers.CharField()
    method_name = serializers.CharField(source="methodName")
    is_preferred = serializers.BooleanField(source="isPreferred")
    beneficiary_account_number = serializers.CharField(source="beneficiaryAccountNumber")
    routing_code = serializers.CharField(source="routingCode")
    routing_code2 = serializers.CharField(source="routingCode2", required=False)


class CorPayBeneficiarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    persistent_id = serializers.UUIDField(source='persistentId')
    beneficiary_contact_name = serializers.CharField(source='beneContactName')
    beneficiary_identifier = serializers.CharField(source='beneIdentifier')
    destination_country = serializers.CharField(source='destinationCountry')
    bank_currency = serializers.CharField(source='bankCurrency')
    beneficiary_classification = serializers.CharField(source='beneClassification')
    beneficiary_country = serializers.CharField(source='beneCountry')
    beneficiary_region = serializers.CharField(source='beneRegion')
    beneficiary_address1 = serializers.CharField(source='beneAddress1')
    beneficiary_address2 = serializers.CharField(source='beneAddress2', required=False)
    beneficiary_city = serializers.CharField(source='beneCity')
    beneficiary_postal = serializers.CharField(source='benePostal')
    beneficiary_phone_number = serializers.CharField(source='beneficiaryPhoneNumber', required=False)
    beneficiary_email = serializers.EmailField(source='beneEmail', required=False)
    send_pay_tracker = serializers.BooleanField(source='sendPayTracker')
    bank_name = serializers.CharField(source='bankName')
    swift_bic_code = serializers.CharField(source='swiftBicCode')
    bank_country = serializers.CharField(source='bankCountry')
    bank_region = serializers.CharField(source='bankRegion')
    bank_city = serializers.CharField(source='bankCity')
    purpose_of_payment = serializers.CharField(source='purposeOfPayment', required=False)
    bank_address_line1 = serializers.CharField(source='bankAddressLine1')
    bank_address_line2 = serializers.CharField(source='bankAddressLine2', required=False)
    bank_postal = serializers.CharField(source='bankPostal')
    payment_reference = serializers.CharField(source='paymentReference', allow_null=True)
    internal_payment_alert = serializers.CharField(source='internalPaymentAlert', required=False)
    external_payment_alert = serializers.CharField(source='externalPaymentAlert', required=False)
    method_of_delivery = serializers.CharField(source='methodOfDelivery', required=False)
    mailing_instructions = serializers.CharField(source='mailingInstructions', required=False)
    regulatory_fields = serializers.CharField(source='regulatoryFields', required=False)
    last_update = serializers.DateTimeField(source='lastUpdate')
    status = serializers.CharField()
    entry_by = serializers.IntegerField(source='entryBy')
    b_bank_id = serializers.CharField(source='bBankId')
    b_bank_address3 = serializers.CharField(source='bBankAddress3')
    b_bank_address4 = serializers.CharField(source='bBankAddress4')
    b_bank_location = serializers.CharField(source='bBankLocation')
    i_bank_swift_bic = serializers.CharField(source='iBankSWIFTBIC')
    i_bank_id = serializers.CharField(source='iBankId')
    i_bank_name = serializers.CharField(source='iBankName')
    i_bank_address1 = serializers.CharField(source='iBankAddress1')
    i_bank_address2 = serializers.CharField(source='iBankAddress2')
    i_bank_address3 = serializers.CharField(source='iBankAddress3')
    i_bank_address4 = serializers.CharField(source='iBankAddress4')
    i_bank_city = serializers.CharField(source='iBankCity')
    i_bank_province = serializers.CharField(source='iBankProvince')
    i_bank_postal_code = serializers.CharField(source='iBankPostalCode')
    i_bank_country_iso = serializers.CharField(source='iBankCountryISO')
    i_bank_location = serializers.CharField(source='iBankLocation')
    default_internal_comment = serializers.CharField(source='defaultInternalComment')
    comment = serializers.CharField()
    sender_to_receiver = serializers.CharField(source='senderToReceiver')
    deal_comment = serializers.CharField(source='dealComment')
    has_docs = serializers.BooleanField(source='hasDocs')
    send202 = serializers.BooleanField()
    beneficiary_owes = serializers.BooleanField(source='beneOwes')
    notify_bank = serializers.BooleanField(source='notifyBank')
    client_code = serializers.IntegerField(source='clientCode')
    to_client = serializers.BooleanField(source='toClient')
    default_remitter_id = serializers.IntegerField(source='defaultRemitterId', required=False)
    account_number = serializers.CharField(source='accountNumber')
    routing_code = serializers.CharField(source='routingCode')
    routing_code2 = serializers.CharField(source='routingCode2', required=False)
    methods = BeneMethodSerializer(many=True)
    payment_methods = serializers.CharField(source='paymentMethods')
    settlement_methods = serializers.CharField(source='settlementMethods')
    preferred_method = serializers.CharField(source='preferredMethod')
    iban = serializers.CharField()
    beneficiary_country_name = serializers.CharField(source='beneCountryName')
    account_holder_country_name = serializers.CharField(source='accountHolderCountryName')
    bank_country_name = serializers.CharField(source='bankCountryName')
    regulatory = serializers.ListField(child=serializers.DictField())
    bank_currency_desc = serializers.CharField(source='bankCurrencyDesc')


class RetrieveBeneficiaryResponseSerializer(serializers.Serializer):
    beneficiary = CorPayBeneficiarySerializer(source='bene')


class DeleteBeneficiaryResponseSerializer(serializers.Serializer):
    advanced = serializers.DictField(required=False)


class ListBeneficiaryRequestSerializer(serializers.Serializer):
    currency = serializers.CharField(required=False)
    payee_country = serializers.CharField(required=False)
    method = serializers.ChoiceField(choices=BENEFICIARY_PAYMENT_METHODS, required=False)
    status = serializers.ChoiceField(choices=BENEFICIARY_STATUSES, required=False)
    skip = serializers.IntegerField(default=0)
    take = serializers.IntegerField(default=100)
    is_withdraw = serializers.BooleanField(required=False)


class ListBeneficiaryRowSerializer(serializers.Serializer):
    bank_city = serializers.CharField(source='bankCity')
    bank_country_iso = serializers.CharField(source='bankCountryISO')
    bank_name = serializers.CharField(source='bankName')
    payee_city = serializers.CharField(source='payeeCity')
    payee_country_iso = serializers.CharField(source='payeeCountryISO')
    payee_country = serializers.CharField(source='payeeCountry')
    id = serializers.UUIDField()
    client_code = serializers.CharField(source='clientCode')
    client_integration_id = serializers.CharField(source='clientIntegrationId')
    curr = serializers.CharField()
    email = serializers.EmailField(required=False)
    methods = ValueSetSerializer(many=True)
    payee = serializers.CharField()
    payment_ref = serializers.CharField(source='paymentRef')
    phone = serializers.CharField()
    entry_date = serializers.DateTimeField(source='entryDate')
    status = ValueSetSerializer(many=True)
    links = LinkSerializer(many=True)


class ListBeneficiaryFacetsSerializer(serializers.Serializer):
    curr = FacetSerializer(many=True)
    methods = FacetSerializer(many=True)
    countries = FacetSerializer(many=True)
    status = FacetSerializer(many=True)


class ListBeneficiaryResponseDataSerializer(ListDataSerializer):
    rows = ListBeneficiaryRowSerializer(many=True)
    withdraw_total = serializers.IntegerField(required=False)


class ListBeneficiaryResponseSerializer(serializers.Serializer):
    data = ListBeneficiaryResponseDataSerializer()
    facets = ListBeneficiaryFacetsSerializer()
    is_beneficiary_approval_required = serializers.BooleanField(source='isBeneApprovalRequired')


class ListBankRequestSerializer(serializers.Serializer):
    country = serializers.CharField()
    query = serializers.CharField(required=False)
    skip = serializers.IntegerField(required=False)
    take = serializers.IntegerField(required=False)


class ListBankRowSerializer(serializers.Serializer):
    primary_key = serializers.CharField(source='primaryKey')
    institution_name = serializers.CharField(source='institutionName')
    address1 = serializers.CharField()
    address2 = serializers.CharField()
    city = serializers.CharField()
    region = serializers.CharField()
    country = serializers.CharField()
    country_iso = serializers.CharField(source="countryISO")
    postal_code = serializers.CharField(source='postalCode')
    swift_bic = serializers.CharField(source="swiftBIC")
    national_bank_code = serializers.CharField(source="nationalBankCode")
    national_bank_code_type = serializers.CharField(source="nationalBankCodeType")
    office_type = serializers.CharField(source="officeType")
    branch_name = serializers.CharField(source="branchName")
    phone = serializers.CharField()
    fax = serializers.CharField()


class ListBankResponseDataSerializer(serializers.Serializer):
    pagination = PaginationSerializer()
    links = LinkSerializer(many=True)
    sorting = SortingSerializer(many=True)
    rows = ListBankRowSerializer(many=True)


class ListBankFacetSerializer(serializers.Serializer):
    regions = FacetSerializer(many=True)
    cities = FacetSerializer(many=True)


class ListBankResponseSerializer(serializers.Serializer):
    data = ListBankResponseDataSerializer()
    facets = ListBankFacetSerializer()


class IbanValidationRequestSerializer(serializers.Serializer):
    iban = serializers.CharField()


class IbanValidationResponseSerializer(serializers.Serializer):
    is_valid = serializers.BooleanField(source="isValid")
    is_warning = serializers.BooleanField(source="isWarning")
    iban = serializers.CharField()
    branch_code = serializers.CharField(source="branchCode")
    routing_number = serializers.CharField(source="routingNumber")
    account_number = serializers.CharField(source="accountNumber")
    swift_bic = serializers.CharField(source="swiftBIC")
    bank_name = serializers.CharField(source="bankName")
    branch_name = serializers.CharField(source="branchName")
    bank_address = serializers.CharField(source="bankAddress")
    postal_code = serializers.CharField(source="postalCode")
    country_name = serializers.CharField(source="countryName")
    country = serializers.CharField()
    bank_city = serializers.CharField(source="bankCity")
    validation_messages = MessageSerializer(source="validationMessages", many=True)
    responses = MessageSerializer(many=True)
    recommended_acct = serializers.CharField(source="recommendedAcct")
