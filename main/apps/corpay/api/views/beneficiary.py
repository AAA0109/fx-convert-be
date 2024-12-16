from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from main.apps.corpay.api.serializers.beneficiary.beneficiary import BeneficiaryRulesRequestSerializer, \
    BeneficiaryRulesResponseSerializer, BeneficiaryRequestSerializer, BeneficiaryResponseSerializer, \
    DeleteBeneficiaryRequestSerializer, RetrieveBeneficiaryResponseSerializer, \
    DeleteBeneficiaryResponseSerializer, ListBeneficiaryRequestSerializer, ListBeneficiaryResponseSerializer, \
    ListBankRequestSerializer, ListBankResponseSerializer, IbanValidationResponseSerializer, \
    IbanValidationRequestSerializer
from main.apps.corpay.api.views.base import CorPayBaseView
from main.apps.corpay.models import Beneficiary, CorpaySettings
from main.apps.corpay.services.api.dataclasses.beneficiary import BeneficiaryRulesQueryParams, BeneficiaryRequestBody, \
    BeneficiaryListQ, BeneficiaryListQueryParams, BankSearchParams, IbanValidationRequestBody
from main.apps.corpay.services.beneficiary.cache import CorPayBeneficiaryCacheService


class RetrieveBeneficiaryRulesView(CorPayBaseView):
    @extend_schema(
        parameters=[BeneficiaryRulesRequestSerializer],
        responses={
            status.HTTP_200_OK: BeneficiaryRulesResponseSerializer
        }
    )
    def get(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = BeneficiaryRulesRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        params = BeneficiaryRulesQueryParams(
            destinationCountry=serializer.validated_data.get('destination_country'),
            bankCountry=serializer.validated_data.get('bank_country'),
            bankCurrency=serializer.validated_data.get('bank_currency'),
            classification=serializer.validated_data.get('rules_classification'),
            paymentMethods=serializer.validated_data.get('payment_method'),
            templateType='Bene'
        )
        response = self.corpay_service.get_beneficiary_rules(data=params)
        response_serializer = BeneficiaryRulesResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class BeneficiaryView(CorPayBaseView):
    @extend_schema(
        request=BeneficiaryRequestSerializer,
        responses={
            status.HTTP_200_OK: BeneficiaryResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = BeneficiaryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        data = BeneficiaryRequestBody(
            accountHolderName=validated_data.get('account_holder_name'),
            templateIdentifier=validated_data.get('template_identifier'),
            destinationCountry=validated_data.get('destination_country'),
            bankCurrency=validated_data.get('bank_currency'),
            classification=validated_data.get('classification'),
            paymentMethods=validated_data.get('payment_methods'),
            preferredMethod=validated_data.get('preferred_method'),
            accountNumber=validated_data.get('account_number'),
            localAccountNumber=validated_data.get('local_account_number'),
            routingCode=validated_data.get('routing_code'),
            localRoutingCode=validated_data.get('local_routing_cote'),
            accountHolderCountry=validated_data.get('account_holder_country'),
            accountHolderRegion=validated_data.get('account_holder_region'),
            accountHolderAddress1=validated_data.get('account_holder_address1'),
            accountHolderAddress2=validated_data.get('account_holder_address2'),
            accountHolderCity=validated_data.get('account_holder_city'),
            accountHolderPostal=validated_data.get('account_holder_postal'),
            accountHolderPhoneNumber=validated_data.get('account_holder_phone_number'),
            accountHolderEmail=validated_data.get('account_holder_email'),
            sendPayTracker=validated_data.get('send_pay_tracker'),
            iban=validated_data.get('iban'),
            swiftBicCode=validated_data.get('swift_bic_code'),
            bankName=validated_data.get('bank_name'),
            bankCountry=validated_data.get('bank_country'),
            bankRegion=validated_data.get('bank_region'),
            bankCity=validated_data.get('bank_city'),
            bankAddressLine1=validated_data.get('bank_address_line1'),
            bankAddressLine2=validated_data.get('bank_address_line2'),
            bankPostal=validated_data.get('bank_postal'),
            paymentReference=validated_data.get('payment_reference'),
            internalPaymentAlert=validated_data.get('internal_payment_alert'),
            externalPaymentAlert=validated_data.get('external_payment_alert'),
            regulatory=validated_data.get('regulatory')
        )
        response = self.corpay_service.upsert_beneficiary(
            data=data,
            company=request.user.company,
            is_withdraw=validated_data.get('is_withdraw')
        )
        service = CorPayBeneficiaryCacheService()
        service.execute(request.user.company.pk)
        response_serializer = BeneficiaryResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)

    @extend_schema(
        parameters=[DeleteBeneficiaryRequestSerializer],
        responses={
            status.HTTP_200_OK: RetrieveBeneficiaryResponseSerializer
        }
    )
    def get(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = DeleteBeneficiaryRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        client_integration_id = serializer.validated_data.get('client_integration_id')
        response = self.corpay_service.get_beneficiary(client_integration_id=client_integration_id)
        response_serializer = RetrieveBeneficiaryResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)

    @extend_schema(
        parameters=[DeleteBeneficiaryRequestSerializer],
        responses={
            status.HTTP_200_OK: DeleteBeneficiaryResponseSerializer
        }
    )
    def delete(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = DeleteBeneficiaryRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        client_integration_id = serializer.validated_data.get('client_integration_id')
        response = self.corpay_service.delete_beneficiary(client_integration_id=client_integration_id)
        response_serializer = DeleteBeneficiaryResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class ListBeneficiaryView(CorPayBaseView):
    @extend_schema(
        parameters=[ListBeneficiaryRequestSerializer],
        responses={
            status.HTTP_200_OK: ListBeneficiaryResponseSerializer
        }
    )
    def get(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = ListBeneficiaryRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        q = BeneficiaryListQ(
            Curr=serializer.validated_data.get('currency'),
            PayeeCountryISO=serializer.validated_data.get('payee_country'),
            Methods=serializer.validated_data.get('method'),
            Status=serializer.validated_data.get('status')
        )
        params = BeneficiaryListQueryParams(
            skip=serializer.validated_data.get('skip'),
            take=serializer.validated_data.get('take'),
            q=q
        )
        response = self.corpay_service.list_beneficiary(data=params)
        try:
            settings = CorpaySettings.objects.get(company=request.user.company)
            if settings.pangea_beneficiary_id is not None:
                response['data']['rows'] = [
                    row for row in response['data']['rows']
                    if row['clientIntegrationId'] != settings.pangea_beneficiary_id
                ]
        except Exception as e:
            ...
        if serializer.validated_data.get('is_withdraw'):
            withdraw_ids = Beneficiary.objects.filter(
                company=request.user.company,
                is_withdraw=True
            )
            withdraw_total = withdraw_ids.count()
            withdraw_ids = [beneficiary.client_integration_id for beneficiary in withdraw_ids]
            filtered_rows = [
                item for item in response['data']['rows']
                if item.get('clientIntegrationId') in withdraw_ids
            ]
            response['data']['rows'] = filtered_rows
            response['data']['withdraw_total'] = withdraw_total
        response_serializer = ListBeneficiaryResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class ListBankView(CorPayBaseView):
    @extend_schema(
        parameters=[ListBankRequestSerializer],
        responses={
            status.HTTP_200_OK: ListBankResponseSerializer
        }
    )
    def get(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = ListBankRequestSerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        params = BankSearchParams(
            country=serializer.validated_data.get('country'),
            query=serializer.validated_data.get('query'),
            skip=serializer.validated_data.get('skip'),
            take=serializer.validated_data.get('take'),
        )
        response = self.corpay_service.list_bank(data=params)
        response_serializer = ListBankResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)


class CreateIBANValidationView(CorPayBaseView):
    @extend_schema(
        request=IbanValidationRequestSerializer,
        responses={
            status.HTTP_200_OK: IbanValidationResponseSerializer
        }
    )
    def post(self, request):
        self.corpay_service.init_company(request.user.company)
        serializer = IbanValidationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = IbanValidationRequestBody(
            iban=serializer.validated_data.get('iban')
        )
        response = self.corpay_service.iban_validation(data=payload)
        response_serializer = IbanValidationResponseSerializer(response)
        return Response(response_serializer.data, status.HTTP_200_OK)
