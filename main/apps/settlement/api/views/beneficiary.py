import logging
import uuid

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from idempotency_key.decorators import idempotency_key
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from main.apps.account.models import Company
from main.apps.core.api.serializers.error import MessageResponseSerializer
from main.apps.core.constants import BENEFICIARY_IDENTIFIER_HELP_TEXT
from main.apps.corpay.api.serializers.beneficiary.beneficiary import ListBankRequestSerializer, \
    ListBankResponseSerializer
from main.apps.corpay.services.api.dataclasses.beneficiary import BankSearchParams
from main.apps.corpay.services.corpay import CorPayService
from main.apps.settlement.api.permissions import BeneficiaryBelongsToCompany
from main.apps.settlement.api.serializers.beneficiary import BeneficiarySerializer, \
    ActivateBeneficiaryRequestSerializer, ValidationSchemaRequestSerializer
from main.apps.settlement.exceptions.beneficiary import InvalidPayoutMethod
from main.apps.settlement.models import Beneficiary
from main.apps.settlement.services.beneficiary import BeneficiaryServiceFactory, BeneficiaryService, \
    BeneficiarySerializerService
from main.apps.settlement.tasks import sync_beneficiary_to_brokers

logger = logging.getLogger(__name__)


class BeneficiaryViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    serializer_class = BeneficiarySerializer
    queryset = Beneficiary.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company = self.request.user.company
        return self.queryset.filter(company=company).exclude(status=Beneficiary.Status.DELETED)

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        identifier = self.kwargs.get('pk')
        if not identifier:
            raise ValidationError({'identifier': 'This field may not be blank.'})

        # Try to parse as UUID first
        try:
            uuid_obj = uuid.UUID(identifier)
            return get_object_or_404(queryset, beneficiary_id=uuid_obj)
        except ValueError:
            # If not a valid UUID, treat as an alias
            if not identifier.strip():  # Check if identifier is just whitespace
                raise ValidationError({'identifier': 'Invalid identifier provided.'})

            # Look up by alias, ensuring it's not empty or null
            return get_object_or_404(
                queryset,
                Q(beneficiary_alias=identifier) &
                ~Q(beneficiary_alias='') &
                ~Q(beneficiary_alias__isnull=True)
            )

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @extend_schema(
        tags=["Settlement"],
        summary="Create Beneficiary",
        description="Endpoint for creating payment instructions for a beneficiary."
    )
    @idempotency_key(optional=True)
    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            if 'unique_beneficiary_alias_per_company' in str(e):
                raise ValidationError({
                    'beneficiary_alias': ['A beneficiary with this alias already exists for this company.']
                })
            else:
                # Re-raise the exception if it's not the specific one we're looking for
                raise

    @extend_schema(
        tags=["Settlement"],
        summary="List Beneficiaries",
        description="Endpoint for listing active beneficiaries."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, *kwargs)

    @extend_schema(
        tags=["Settlement"],
        summary="Retrieve Beneficiary",
        description="Endpoint for retrieving a specific beneficiary.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description=BENEFICIARY_IDENTIFIER_HELP_TEXT
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        self.permission_classes = [IsAuthenticated, BeneficiaryBelongsToCompany]
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["Settlement"],
        summary="Replace Beneficiary",
        description="Endpoint for replacing existing beneficiary data with a new set of data.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description=BENEFICIARY_IDENTIFIER_HELP_TEXT
            )
        ]
    )
    def update(self, request, *args, **kwargs):
        self.permission_classes = [IsAuthenticated, BeneficiaryBelongsToCompany]
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_update(serializer)
        except IntegrityError:
            return Response(
                {"detail": "A beneficiary with this alias already exists in this company."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data)

    @extend_schema(
        tags=["Settlement"],
        summary="Update Beneficiary",
        description="Endpoint for partially updating an existing beneficiary.",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description=BENEFICIARY_IDENTIFIER_HELP_TEXT
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        self.permission_classes = [IsAuthenticated, BeneficiaryBelongsToCompany]
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        tags=["Settlement"],
        summary="Delete Beneficiary",
        description="Endpoint for deleting a beneficiary",
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description=BENEFICIARY_IDENTIFIER_HELP_TEXT
            )
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        tags=["Settlement"],
        summary="Activate Beneficiary",
        description="Endpoint for activating a beneficiary from draft to pending",
        request=ActivateBeneficiaryRequestSerializer,
        responses={
            status.HTTP_200_OK: MessageResponseSerializer,
            status.HTTP_400_BAD_REQUEST: MessageResponseSerializer
        }
    )
    @action(detail=False, methods=['POST'], permission_classes=[IsAuthenticated, BeneficiaryBelongsToCompany])
    def activate(self, request, *args, **kwargs):
        request_serializer = ActivateBeneficiaryRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        identifier = request_serializer.validated_data['identifier']
        try:
            beneficiary = Beneficiary.objects.get(
                Q(beneficiary_id=identifier) | Q(beneficiary_alias=identifier),
                company=request.user.company
            )
            if beneficiary.status == Beneficiary.Status.DRAFT:
                beneficiary.status = Beneficiary.Status.PENDING
                beneficiary.save(update_fields=['status'])
                sync_beneficiary_to_brokers(beneficiary.pk)
                response_data = {'message': 'Beneficiary activated successfully.'}
                response_serializer = MessageResponseSerializer(data=response_data)
                response_serializer.is_valid(raise_exception=True)
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                response_data = {'message': 'Beneficiary is not in draft status.'}
                response_serializer = MessageResponseSerializer(data=response_data)
                response_serializer.is_valid(raise_exception=True)
                return Response(response_serializer.data, status=status.HTTP_400_BAD_REQUEST)
        except Beneficiary.DoesNotExist:
            response_data = {'message': 'Beneficiary not found.'}
            response_serializer = MessageResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(e)
            message = 'Unable to activate beneficiary'
            if settings.APP_ENVIRONMENT in ['dev', 'local']:
                message += f": {e}"
                beneficiary.status = Beneficiary.Status.DRAFT
                beneficiary.save(update_fields=['status'])
            response_data = {'message': message}
            response_serializer = MessageResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        tags=["Settlement"],
        summary="Beneficiary Validation Schema",
        description="Endpoint for getting validation schema for creating a beneficiary",
        request=ValidationSchemaRequestSerializer
    )
    @action(detail=False, methods=['POST'], permission_classes=[IsAuthenticated])
    def validation_schema(self, request, *args, **kwargs):
        request_serializer = ValidationSchemaRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        bank_currency = request_serializer.validated_data.get('bank_currency')
        destination_country = request_serializer.validated_data.get('destination_country')
        bank_country = request_serializer.validated_data.get('bank_country')
        beneficiary_account_type = request_serializer.validated_data.get('beneficiary_account_type')
        payment_method = request_serializer.validated_data.get('payment_method')

        factory = BeneficiaryServiceFactory(company=request.user.company)
        services = factory.create_beneficiary_services(currency=bank_currency)
        schemas = []
        beneficiary_serializer_service = BeneficiarySerializerService(BeneficiaryViewSet)
        beneficiary_serializer_schema = beneficiary_serializer_service.get_schema(bank_currency)
        schemas.append(beneficiary_serializer_schema)
        for service in services:
            try:
                schema = service.get_beneficiary_validation_schema(
                    destination_country=destination_country,
                    bank_country=bank_country,
                    bank_currency=bank_currency,
                    beneficiary_account_type=beneficiary_account_type,
                    payment_method=payment_method,
                )
                if schema is None:
                    continue
                if isinstance(schema, list):
                    schemas.extend(schema)
                else:
                    schemas.append(schema)
            except InvalidPayoutMethod as e:
                logger.warning(
                    f"{request.user.company} requested an invalid validation schema using: "
                    f"destination country: {destination_country}, bank country: {bank_country}, "
                    f"bank currency: {bank_currency}, beneficiary_account_type: {beneficiary_account_type}, "
                    f"payment_method: {payment_method} from broker: {service.broker.name}")
                logger.warning(e)
            except Exception as e:
                logger.exception(e)
                continue
        merged = BeneficiaryService.merge_validation_schemas(schemas)
        response_data = {"schemas": schemas, "merged": merged}
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def bank_search(self, request, *args, **kwargs):
        results = perform_search(request)
        if results is None:
            return Response({"error": "Corpay company not found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(results, status=status.HTTP_200_OK)


def perform_search(request):
    company_id = settings.CORPAY_PANGEA_COMPANY_ID
    if company_id is None:
        return None
    c = Company.objects.get(pk=company_id)
    if c is None:
        return None
    corpay_service = CorPayService()
    corpay_service.init_company(company=c)
    serializer = ListBankRequestSerializer(data=request.GET)
    serializer.is_valid(raise_exception=True)
    params = BankSearchParams(
        country=serializer.validated_data.get('country'),
        query=serializer.validated_data.get('query'),
        skip=serializer.validated_data.get('skip'),
        take=serializer.validated_data.get('take'),
    )
    response = corpay_service.list_bank(data=params)
    response_serializer = ListBankResponseSerializer(response)
    return response_serializer.data
