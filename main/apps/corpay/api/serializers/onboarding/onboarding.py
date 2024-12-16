from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from main.apps.account.models import Company
from main.apps.corpay.api.fields.file import OnboardingFileField
from main.apps.corpay.models.onboarding import OnboardingFile


class CompanyDirectorsSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    job_title = serializers.CharField()
    occupation = serializers.CharField()


class BeneficialOwnerSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    nationality = serializers.CharField()
    ssn = serializers.CharField()
    residential_address = serializers.CharField()
    ownership_percentage = serializers.FloatField()
    beneficiary_owner_dob = serializers.DateField(required=False)


class OnboardingRequestSerializer(serializers.Serializer):
    company_name = serializers.CharField()
    company_street_address = serializers.CharField()
    company_city = serializers.CharField()
    company_postal_code = serializers.CharField()
    company_country_code = serializers.CharField()
    business_contact_number = PhoneNumberField()
    business_confirmation_email = serializers.EmailField()
    formation_incorporation_country_code = serializers.CharField()
    business_registration_incorporation_number = serializers.CharField()
    application_type_id = serializers.CharField()
    nature_of_business = serializers.CharField()
    purpose_of_transaction_id = serializers.CharField()
    currency_needed = serializers.ListSerializer(child=serializers.CharField())
    trade_volume = serializers.CharField()
    annual_volume = serializers.CharField()
    fund_destination_countries = serializers.ListSerializer(child=serializers.CharField())
    fund_source_countries = serializers.ListSerializer(child=serializers.CharField())
    company_directors = CompanyDirectorsSerializer(many=True, default=[])
    any_individual_own_25_percent_or_more = serializers.BooleanField()
    provide_truthful_information = serializers.BooleanField()
    agree_to_terms_and_condition = serializers.BooleanField()
    consent_to_privacy_notice = serializers.BooleanField()
    authorized_to_bind_client_to_agreement = serializers.BooleanField()
    signer_full_name = serializers.CharField()
    signer_date_of_birth = serializers.DateField()
    signer_job_title = serializers.CharField()
    signer_email = serializers.EmailField()
    signer_complete_residential_address = serializers.CharField()
    is_account_owner = serializers.BooleanField()
    account_owner_first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    account_owner_last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    account_owner_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    account_owner_phone = PhoneNumberField(required=False, allow_blank=True, allow_null=True)
    dba_or_registered_tradename = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    company_state = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    business_confirmation_email_2 = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    is_publicly_traded = serializers.BooleanField(required=False)
    stock_symbol = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    formation_incorporation_state = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    tax_id_ein_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    business_type_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    website_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    owned_by_other_corporate_entity = serializers.BooleanField(required=False)
    owned_by_public_traded_company = serializers.BooleanField(required=False)
    beneficial_owners = BeneficialOwnerSerializer(many=True, required=False, default=[])
    second_signer_full_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    second_signer_date_of_birth = serializers.DateField(required=False)
    second_signer_job_title = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    second_signer_complete_residential_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    service_interested_in = serializers.MultipleChoiceField(choices=Company.ServiceInterestedIn.choices)


class OnboardingResponseSerializer(serializers.Serializer):
    client_onboarding_id = serializers.CharField(source="clientOnboardingId")
    message = serializers.CharField()


class OnboardingFileUploadRequestSerializer(serializers.Serializer):
    client_onboarding_id = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = OnboardingFileField()


class OnboardingFileUploadResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
