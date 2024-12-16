import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from main.apps.account.api.serializers.cashflow import *
from main.apps.account.api.services.customer import CustomerAPIService
from main.apps.account.models import Account, CashFlowNote
from main.apps.account.permissions.cashflow import CanApproveCashflow
from main.apps.billing.services.new_cash_fee import NewCashFeeService
from main.apps.core.utils.api import *
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


# ====================================================================
#  Cashflows
# ====================================================================


class CashflowViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    queryset = CashFlow.objects.all()

    def get_permissions(self):
        permission_classes = super().get_permissions()
        if self.action == 'approve':
            permission_classes += [CanApproveCashflow()]
        return permission_classes

    @extend_schema(
        parameters=[
            OpenApiParameter(name='with_installments',
                             location=OpenApiParameter.QUERY,
                             description='Whether to include installments',
                             type=OpenApiTypes.BOOL,
                             required=False,
                             default=True),
            OpenApiParameter(name='installment',
                             location=OpenApiParameter.QUERY,
                             description='Query a specific installment',
                             type=OpenApiTypes.STR,
                             required=False),
        ],
        responses={
            status.HTTP_200_OK: CashflowSerializer(many=True)
        }
    )
    def list(self, request, account_pk: int):
        """
        Get all the cashflows for an account
        """

        accounts = Account.get_account_objs(company=request.user.company_id)
        account = get_object_or_404(accounts, pk=account_pk)
        cashflows = self.queryset.filter(account=account).exclude(status__in=[
            CashFlow.CashflowStatus.PENDING_DEACTIVATION,
            CashFlow.CashflowStatus.INACTIVE
        ])
        exclude_installments = request.query_params.get('with_installments', 'true') != 'true'
        if exclude_installments:
            cashflows = cashflows.filter(installment__isnull=True)
        if request.query_params.get('installment'):
            cashflows = cashflows.filter(installment__pk=request.query_params.get('installment'))
        serializer = CashflowSerializer(cashflows, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=CashFlowCoreSerializer,
        parameters=[
            OpenApiParameter(name='include_pending_margin_in_margin_check',
                             location=OpenApiParameter.QUERY,
                             description='Whether to include pending margin in health check',
                             type=OpenApiTypes.BOOL,
                             required=False,
                             default=True),
        ],
        responses={
            status.HTTP_201_CREATED: CashflowSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: CashFlowActionStatusSerializer
        }
    )
    def create(self, request, account_pk: int):
        """
        Add a cashflow for an account
        """
        accounts = Account.get_account_objs(company=request.user.company_id)
        account = get_object_or_404(accounts, pk=account_pk)

        serializer = CashFlowCoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        include_pending_margin_in_margin_check = request.query_params.get('include_pending_margin_in_margin_check',
                                                                          'true') == 'true'

        # Validate that the customer is setup to be charged with stripe.
        company = account.company
        if not company.stripe_setup_intent_id:
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus.error(
                    message="Error: Bad Request, Company Missing Stripe Setup Intent",
                    code='missing_setup_intent'
                )
            )
        try:
            with transaction.atomic():

                # Create the cashflow
                customer_api = CustomerAPIService()
                cashflow_obj = customer_api.add_cashflow(
                    user=request.user,
                    account_id=account,
                    date=serializer.validated_data.get('pay_date'),
                    currency_id=serializer.validated_data.get('currency'),
                    amount=serializer.validated_data.get('amount'),
                    name=serializer.validated_data.get('name'),
                    description=serializer.validated_data.get('description'),
                    periodicity=serializer.validated_data.get('periodicity'),
                    calendar=serializer.get_calendar(),
                    end_date=serializer.validated_data.get('end_date'),
                    installment_id=serializer.validated_data.get('installment'),
                    roll_convention=serializer.validated_data.get('roll_convention'),
                    include_pending_margin_in_margin_check=include_pending_margin_in_margin_check,
                )
                fee_service = NewCashFeeService()
                spot_fx_cache = FxSpotProvider().get_spot_cache()
                fee_service.create_new_cashflow_fee(
                    spot_fx_cache=spot_fx_cache,
                    cashflow=cashflow_obj
                )

                serializer = CashflowSerializer(cashflow_obj)
                data = serializer.data

                return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating new cashflow: {e}")
            return get_response_from_action_status(
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                action_status=ActionStatus.error(
                    message=f"Error: failed to process Payment: {e}",
                    code='internal_server_error'
                )
            )

    @extend_schema(
        request=CashFlowCoreSerializer,
        responses={
            status.HTTP_200_OK: CashflowSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: CashFlowActionStatusSerializer
        }
    )
    def update(self, request, account_pk: int, pk: int = None):
        """
        Replace an existing cashflow with a new one, effectively 'updating' or 'editing' a cashflow
        """
        accounts = Account.get_account_objs(company=request.user.company_id)
        account = get_object_or_404(accounts, pk=account_pk)
        serializer = CashFlowCoreSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        # Validate that the customer is setup to be charged with stripe.
        company = account.company
        if not company.stripe_setup_intent_id:
            return get_response_from_action_status(
                http_status=status.HTTP_400_BAD_REQUEST,
                action_status=ActionStatus.error(
                    message="Error: Bad Request, Company Missing Stripe Setup Intent",
                    code='missing_setup_intent'
                )
            )

        try:
            with transaction.atomic():
                # Note: we wrap this up in an atomic transaction, so that if the charging of fee raises,
                # then the cashflow edits will be rolled back
                cashflow_obj = CustomerAPIService().edit_cashflow(
                    account_id=account,
                    cashflow_id=pk,
                    amount=serializer.validated_data.get('amount'),
                    currency_id=serializer.validated_data.get('currency'),
                    pay_date=serializer.validated_data.get('pay_date'),
                    name=serializer.validated_data.get('name'),
                    description=serializer.validated_data.get('description'),
                    periodicity=serializer.validated_data.get('periodicity'),
                    calendar=serializer.get_calendar(),
                    end_date=serializer.validated_data.get('end_date'),
                    installment_id=serializer.validated_data.get('installment'),
                    roll_convention=serializer.validated_data.get('roll_convention'))

                fee_service = NewCashFeeService()
                spot_fx_cache = FxSpotProvider().get_spot_cache()
                fee_service.create_new_cashflow_fee(spot_fx_cache=spot_fx_cache, cashflow=cashflow_obj)

                serializer = CashflowSerializer(cashflow_obj)
                data = serializer.data

                return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error for cashflow edit: {e}")

            return get_response_from_action_status(
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                action_status=ActionStatus.error(
                    message=f"Error: failed to process Payment: {e}",
                    code='internal_server_error'
                )
            )

    @extend_schema(
        responses={
            status.HTTP_204_NO_CONTENT: None,
        }
    )
    def destroy(self, request, account_pk: int, pk: int = None):
        """
        Remove a cashflow from an account
        """
        accounts = Account.get_account_objs(company=request.user.company_id)
        account = get_object_or_404(accounts, pk=account_pk)

        CustomerAPIService().remove_cashflow(
            account_id=account,
            cashflow_id=pk
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        responses={
            status.HTTP_200_OK: CashflowSerializer
        }
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='approve'
    )
    def approve(self, request, account_pk: int, pk: int = None):
        """
        Approve a cashflow from an account
        """
        accounts = Account.get_account_objs(company=request.user.company_id)
        get_object_or_404(accounts, pk=account_pk)

        cashflow = CustomerAPIService().approve_cashflow(cashflow_id=pk)
        serializer = CashflowSerializer(cashflow)
        data = serializer.data
        return Response(data, status=status.HTTP_200_OK)

    class Draft(viewsets.GenericViewSet):
        permission_classes = [IsAuthenticated, HasCompanyAssociated]
        serializer_class = DraftCashflowSerializer
        allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')
        queryset = CashFlow.objects.all()

        @extend_schema(
            request=DraftCashflowSerializer,
            responses={
                status.HTTP_201_CREATED: DraftCashflowSerializer,
            }
        )
        def create(self, request, account_pk: int, cashflow_pk: int):
            cashflow = get_object_or_404(self.get_queryset(), pk=cashflow_pk, account_id=account_pk)
            serializer = DraftCashflowSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            installment_id = serializer.validated_data.get('installment_id', None)
            if installment_id:
                installment = InstallmentCashflow.get_installment(
                    request.user.company,
                    installment_id)
            else:
                installment = None
            if serializer.validated_data.get('account_id', None):
                account = Account.get_account(serializer.validated_data.get('account_id'))
            else:
                account = cashflow.account
            with transaction.atomic():
                draft = DraftCashFlow.objects.create(
                    date=serializer.date,
                    amount=serializer.amount,
                    currency=Currency.get_currency(serializer.currency_mnemonic),
                    name=serializer.name,
                    description=serializer.description,
                    periodicity=serializer.periodicity,
                    calendar=serializer.calendar,
                    end_date=serializer.end_date,
                    company=self.request.user.company,
                    installment=installment,
                    action=serializer.validated_data.get('action'),
                    account=account,
                    indicative_rate=serializer.validated_data.get('indicative_rate'),
                    indicative_base_amount=serializer.validated_data.get('indicative_base_amount'),
                    indicative_cntr_amount=serializer.validated_data.get('indicative_cntr_amount')
                )
                cashflow.draft = draft
                cashflow.save()

            serializer = DraftCashflowSerializer(draft)
            data = serializer.data

            return Response(data, status=status.HTTP_201_CREATED)

        @extend_schema(
            responses={
                status.HTTP_204_NO_CONTENT: None,
            }
        )
        def destroy(self, request, account_pk: int, cashflow_pk: int, pk: int):
            """
            Remove a cashflow from an account
            """

            cashflow = get_object_or_404(self.get_queryset(), pk=cashflow_pk, account_id=account_pk)
            draft = cashflow.draft
            with transaction.atomic():
                if draft:
                    draft.delete()
                    cashflow.draft = None
                    cashflow.save()

            return Response(status=status.HTTP_204_NO_CONTENT)

        def update(self, request, account_pk: int, cashflow_pk: int, pk: int):
            cashflow = get_object_or_404(self.get_queryset(), pk=cashflow_pk, account_id=account_pk)
            draft = cashflow.draft
            serializer = DraftCashflowSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if serializer.validated_data.get('installment_id', None):
                installment = InstallmentCashflow.get_installment(request.user.company, serializer.installment_id)
            else:
                installment = None
            with transaction.atomic():
                draft.date = serializer.date
                draft.amount = serializer.amount
                draft.currency = Currency.get_currency(serializer.currency_mnemonic)
                draft.name = serializer.name
                draft.description = serializer.description
                draft.periodicity = serializer.periodicity
                draft.calendar = serializer.calendar
                draft.end_date = serializer.end_date
                draft.installment = installment
                draft.account_id = serializer.validated_data.get('account_id')
                draft.action = serializer.validated_data.get('action')
                draft.save()
                cashflow.save()

            serializer = DraftCashflowSerializer(draft)
            data = serializer.data

            return Response(data, status=status.HTTP_200_OK)

        @extend_schema(
            responses={
                status.HTTP_200_OK: CashflowSerializer,
                status.HTTP_500_INTERNAL_SERVER_ERROR: CashFlowActionStatusSerializer
            }
        )
        @action(detail=True, methods=['put'])
        def activate(self, request, account_pk: int, cashflow_pk: int, pk: int):
            cashflow = get_object_or_404(self.get_queryset(),
                                         pk=cashflow_pk, account_id=account_pk)
            # Validate that the customer is setup to be charged with stripe.
            company = cashflow.account.company
            if not company.stripe_setup_intent_id:
                return get_response_from_action_status(
                    http_status=status.HTTP_400_BAD_REQUEST,
                    action_status=ActionStatus.error(
                        message="Error: Bad Request, Company Missing Stripe Setup Intent",
                        code='missing_setup_intent'
                    )
                )

            try:
                with transaction.atomic():
                    cashflow.update_from_draft()
                    if cashflow.draft is not None:
                        cashflow.draft.delete()
                        cashflow.draft = None

                    # Charge a fee
                    fee_service = NewCashFeeService()
                    spot_fx_cache = FxSpotProvider().get_spot_cache()
                    fee_service.create_new_cashflow_fee(spot_fx_cache=spot_fx_cache,
                                                        cashflow=cashflow)

                    cashflow.save()
            except Exception as e:
                logger.error(f"Error activating for cashflow: {e}")

                return get_response_from_action_status(
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    action_status=ActionStatus.error(
                        message=f"Error: failed to process Payment: {e}",
                        code='internal_server_error'
                    )
                )

            return Response(status=status.HTTP_200_OK,
                            data=CashflowSerializer(cashflow).data)


class CashflowNoteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    queryset = CashFlowNote.objects.all()

    @extend_schema(
        parameters=[
        ],
        responses={
            status.HTTP_200_OK: CashflowNoteSerializer(many=True)
        }
    )
    def list(self, request, account_pk: int, cashflow_pk: int):
        """
        Get all Notes from a Cashflow
        """
        accounts = Account.get_account_objs(company=request.user.company_id)
        account = get_object_or_404(accounts, pk=account_pk)
        cashflow = get_object_or_404(CashFlow.objects.filter(account=account), pk=cashflow_pk)
        notes = cashflow.notes
        serializer = CashflowNoteSerializer(notes, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=CashflowNoteSerializer,
        parameters=[
        ],
        responses={
            status.HTTP_201_CREATED: CashflowNoteSerializer,
        }
    )
    def create(self, request, account_pk: int, cashflow_pk: int):
        """
        Add a Note for a Cashflow
        """
        accounts = Account.get_account_objs(company=request.user.company_id)
        account = get_object_or_404(accounts, pk=account_pk)
        cashflow = get_object_or_404(CashFlow.objects.filter(account=account), pk=cashflow_pk)
        serializer = CashflowNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note_obj = CashFlowNote.objects.create(
            cashflow=cashflow,
            description=serializer.validated_data.get('description'),
            created_by=request.user,
            modified_by=request.user,
        )

        serializer = CashflowNoteSerializer(note_obj)
        data = serializer.data

        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=CashflowNoteSerializer,
        responses={
            status.HTTP_200_OK: CashflowNoteSerializer,
        }
    )
    def update(self, request, account_pk: int, cashflow_pk: int, pk: int):
        """
        Update a Note
        """
        accounts = Account.get_account_objs(company=request.user.company_id)
        account = get_object_or_404(accounts, pk=account_pk)
        cashflow = get_object_or_404(CashFlow.objects.filter(account=account), pk=cashflow_pk)
        serializer = CashflowNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note_obj = get_object_or_404(CashFlowNote, pk=pk, cashflow=cashflow)
        note_obj.description = serializer.validated_data.get('description')
        note_obj.modified_by = request.user
        note_obj.save()

        serializer = CashflowNoteSerializer(note_obj)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)
