from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from main.apps.corpay.api.serializers.onboarding.onboarding import OnboardingRequestSerializer, \
    OnboardingResponseSerializer, OnboardingFileUploadRequestSerializer, OnboardingFileUploadResponseSerializer
from main.apps.corpay.api.serializers.onboarding.picklist import OnboardingPickListRequestSerializer, \
    OnboardingPickListResponseSerializer
from main.apps.corpay.api.views.base import CorPayBaseView
from main.apps.corpay.models.onboarding import OnboardingFile, Onboarding
from main.apps.corpay.services.api.dataclasses.onboarding import OnboardingRequestBody, CompanyDirector, \
    BeneficialOwner, OnboardingPickListParams


class CreateClientOnboardingView(CorPayBaseView):
    @extend_schema(
        request=OnboardingRequestSerializer,
        responses={
            status.HTTP_200_OK: OnboardingResponseSerializer
        }
    )
    def post(self, request):
        company = request.user.company
        onboarding_model = Onboarding.objects.filter(
            company=company
        )
        if onboarding_model.exists():
            # If Onboarding exists return the previously created client onboarding id
            onboarding_model = onboarding_model.first()
            data = {
                "clientOnboardingId": onboarding_model.client_onboarding_id,
                "message": "Onboarding record already exist!"
            }
            response_serializer = OnboardingResponseSerializer(data)
            return Response(response_serializer.data, status.HTTP_200_OK)

        serializer = OnboardingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company.service_interested_in = serializer.validated_data.get('service_interested_in')
        company.save()
        payload = OnboardingRequestBody(
            companyName=serializer.validated_data.get('company_name'),
            companyStreetAddress=serializer.validated_data.get('company_street_address'),
            companyCity=serializer.validated_data.get('company_city'),
            companyPostalCode=serializer.validated_data.get('company_postal_code'),
            companyCountryCode=serializer.validated_data.get('company_country_code'),
            businessContactNumber=str(serializer.validated_data.get('business_contact_number')),
            businessConfirmationEmail=serializer.validated_data.get('business_confirmation_email'),
            businessRegistrationIncorporationNumber=serializer.validated_data.get(
                'business_registration_incorporation_number'
            ),
            applicantTypeId=serializer.validated_data.get('applicant_type_id'),
            natureOfBusiness=serializer.validated_data.get('nature_of_business'),
            purposeOfTransactionId=serializer.validated_data.get('purpose_of_transaction_id'),
            currencyNeeded=','.join(serializer.validated_data.get('currency_needed')),
            tradeVolume=serializer.validated_data.get('trade_volume'),
            annualVolume=serializer.validated_data.get('annual_volume'),
            fundDestinationCountries=','.join(serializer.validated_data.get('fund_destination_countries')),
            fundSourceCountries=','.join(serializer.validated_data.get('fund_source_countries')),
            companyDirectors=[CompanyDirector(
                fullName=director.get('full_name'),
                jobTitle=director.get('job_title'),
                occupation=director.get('occupation')
            ) for director in serializer.validated_data.get('company_directors')],
            anyIndividualOwn25PercentOrMore=serializer.validated_data.get('any_individual_own_25_percent_or_more'),
            provideTruthfulInformation=serializer.validated_data.get('provide_truthful_information'),
            agreeToTermsAndConditions=serializer.validated_data.get('agree_to_terms_and_conditions'),
            consentToPrivacyNotice=serializer.validated_data.get('consent_to_privacy_notice'),
            authorizedToBindClientToAgreement=serializer.validated_data.get('authorized_to_bind_client_to_agreement'),
            signerFullName=serializer.validated_data.get('signer_full_name'),
            signerDateOfBirth=serializer.validated_data.get('signer_date_of_birth').strftime("%m/%d/%Y"),
            signerJobTitle=serializer.validated_data.get('signer_job_title'),
            signerEmail=serializer.validated_data.get('signer_email'),
            signerCompleteResidentialAddress=serializer.validated_data.get('signer_complete_residential_address'),
            DBAOrRegisteredTradeName=serializer.validated_data.get('dba_or_registered_trade_name'),
            companyState=serializer.validated_data.get('company_state'),
            businessConfirmationEmail2=serializer.validated_data.get('business_confirmation_email_2'),
            isPubliclyTraded=serializer.validated_data.get('is_publicly_traded'),
            stockSymbol=serializer.validated_data.get('stock_symbol'),
            formationIncorportationCountryCode=serializer.validated_data.get('formation_incorportation_country_code'),
            formationIncorportationState=serializer.validated_data.get('formation_incorportation_state'),
            taxIDEINNumber=serializer.validated_data.get('tax_id_ein_number'),
            businessTypeId=serializer.validated_data.get('business_type_id'),
            websiteUrl=serializer.validated_data.get('website_url'),
            ownedByOtherCorporateEntity=serializer.validated_data.get('owned_by_other_corporate_entity'),
            ownedByPubliclyTradedCompany=serializer.validated_data.get('owned_by_publicly_traded_company'),
            ownedByPubliclyTradedCompanyStockSymbol=serializer.validated_data.get(
                'owned_by_publicly_traded_company_stock_symbol'
            ),
            beneficialOwners=[
                BeneficialOwner(
                    fullName=beneficial_owner.get('full_name'),
                    nationality=beneficial_owner.get('nationality'),
                    ssn=beneficial_owner.get('ssn'),
                    residentialAddress=beneficial_owner.get('residential_address'),
                    ownershipPercentage=beneficial_owner.get('ownership_percentage'),
                    beneficialOwnerDOB=beneficial_owner.get('beneficial_owner_dob')
                ) for beneficial_owner in serializer.validated_data.get('beneficial_owners')
            ],
            secondSignerFullName=serializer.validated_data.get('second_signer_full_name'),
            secondSignerJobTitle=serializer.validated_data.get('second_signer_job_title'),
            secondSignerEmail=serializer.validated_data.get('second_signer_email'),
            secondSignerCompleteResidentialAddress=serializer.validated_data.get(
                'second_signer_complete_residential_address'
            )
        )
        response = self.corpay_service.client_onboarding(data=payload)
        onboarding_model = Onboarding(
            company=request.user.company,
            client_onboarding_id=response['clientOnboardingId']
        )
        onboarding_model.save()
        response_serializer = OnboardingResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class RetrieveOnboardingPickListView(CorPayBaseView):
    @extend_schema(
        parameters=[OnboardingPickListRequestSerializer],
        responses={
            status.HTTP_200_OK: OnboardingPickListResponseSerializer
        }
    )
    def get(self, request):
        serializer = OnboardingPickListRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        params = OnboardingPickListParams(
            pickListType=serializer.validated_data.get('pick_list_type')
        )
        response = self.corpay_service.onboarding_picklist(data=params)
        response_serializer = OnboardingPickListResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class CreateClientOnboardingFileUploadView(CorPayBaseView):
    @extend_schema(
        request=OnboardingFileUploadRequestSerializer,
        responses={
            status.HTTP_200_OK: OnboardingFileUploadResponseSerializer
        }
    )
    def post(self, request):
        serializer = OnboardingFileUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_onboarding_id = serializer.validated_data.get('client_onboarding_id')
        onboarding = Onboarding.objects.get(client_onboarding_id=client_onboarding_id)
        onboarding_file = OnboardingFile(
            company=request.user.company,
            uploaded_by=request.user,
            title=serializer.validated_data.get('title'),
            file=serializer.validated_data.get('file'),
            status=OnboardingFile.FileStatus.NEW,
            onboarding=onboarding
        )
        onboarding_file.save()

        corpay_files = [(
                serializer.validated_data.get('title'),
                ('file', serializer.validated_data['file'].read(), 'application/octet-stream')
        )]

        response = self.corpay_service.client_onboarding_files(
            client_onboarding_id=client_onboarding_id,
            files=corpay_files
        )

        onboarding_file.status = OnboardingFile.FileStatus.SENT_TO_CORPAY
        onboarding_file.save()

        response_serializer = OnboardingFileUploadResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)
