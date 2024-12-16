from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets, mixins, generics
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from main.apps.account.api.serializers.company import (
    CompanySerializer,
    CreateCompanySerializer,
    CompanyContactOrderSerializer,
    CompanyContactOrderRequestSerializer,
    GetCompanyByEINRequestSerializer, CompanyJoinRequestSerializer, CreateCompanyJoinRequestSerializer,
    ApproveCompanyJoinRequestSerializer, RejectCompanyJoinRequestSerializer
)
from main.apps.account.api.serializers.user import UserSerializer
from main.apps.account.api.services.customer import CustomerAPIService
from main.apps.account.models import Company, CompanyContactOrder, User, Currency, CompanyJoinRequest
from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.core.utils.api import HasCompanyAssociated, UserBelongsToCompany, get_response_from_action_status, \
    IsAccountOwner
from main.apps.currency.api.serializers.models.currency import CurrencySerializer
from main.apps.marketdata.services.fx.fx_market_convention_service import FxMarketConventionService
from main.apps.notification.utils.email import send_company_join_request_email
from main.apps.util import ActionStatus


# ====================================================================
#  Company management
# ====================================================================

class CompanyViewSet(ViewSet):
    queryset = Company.objects.all()

    def get_permissions(self):
        if self.action in ['create']:
            self.permission_classes = [IsAuthenticated, ]
        elif self.action in ['deactivate', 'list']:
            self.permission_classes = [IsAuthenticated, HasCompanyAssociated]
        else:
            self.permission_classes = [IsAuthenticated, HasCompanyAssociated, UserBelongsToCompany]

        return super(CompanyViewSet, self).get_permissions()

    @extend_schema(
        responses={
            status.HTTP_200_OK: CompanySerializer
        }
    )
    def list(self, request):
        """
        Get user company
        """
        serializer = CompanySerializer(request.user.company)
        return Response([serializer.data])

    @extend_schema(
        request=CreateCompanySerializer,
        responses={
            status.HTTP_201_CREATED: CompanySerializer
        }
    )
    def create(self, request):
        """
        Create a company
        """
        serializer = CreateCompanySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company_name: str = serializer.data.get('name')
        currency = serializer.data.get('currency')

        try:
            company_obj, _ = CustomerAPIService().create_company(
                company_name=company_name,
                currency=currency)
            company_obj.account_owner = request.user
            company_obj.save()
        except Company.AlreadyExists as e:
            return Response({
                'message': e.message,
                'field': "name"
            }, status.HTTP_409_CONFLICT)

        request.user.company = company_obj
        request.user.save()

        serializer = CompanySerializer(company_obj)
        data = serializer.data

        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=CompanySerializer,
        responses={
            status.HTTP_200_OK: CompanySerializer,
            status.HTTP_400_BAD_REQUEST: ValidationError
        }
    )
    def update(self, request, *args, **kwargs):
        """
        Update a company
        """
        partial = kwargs.pop('partial', False)
        company = request.user.company
        serializer = CompanySerializer(company, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if getattr(company, '_prefetched_objects_cache', None):
            company._prefetched_objects_cache = {}

        return Response(serializer.data)

    @extend_schema(
        request=CompanySerializer,
        responses={
            status.HTTP_200_OK: CompanySerializer,
            status.HTTP_400_BAD_REQUEST: ValidationError
        }
    )
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        responses={
            status.HTTP_202_ACCEPTED: None,
        }
    )
    @action(detail=False, methods=['put'])
    def deactivate(self, request):
        """
        Deactivate a company

        Note that this will lead to all accounts for the company being deactivated and all hedges
        being unwound.
        """
        company_id: int = request.user.company.pk
        CustomerAPIService().deactivate_company(
            company_id=company_id
        )
        return Response(status=status.HTTP_202_ACCEPTED)


class CompanySupportedCurrencyViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    queryset = Currency.objects.all()

    @extend_schema(
        responses={
            status.HTTP_200_OK: CurrencySerializer(many=True)
        }
    )
    def list(self, request, company_pk: int):
        """ Get all currency definitions """
        # TODO: in the future, we will need to find supported currencies accross supported brokers for the company

        convention_service = FxMarketConventionService()
        converter = convention_service.make_fx_market_converter(is_hedge_supported_only=True)
        currencies = converter.get_traded_currencies()
        serializer = CurrencySerializer(currencies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompanyUserViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated, UserBelongsToCompany]
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @extend_schema(
        responses={
            status.HTTP_200_OK: UserSerializer(many=True)
        }
    )
    def list(self, request, company_pk: int):
        company = Company.get_company(int(company_pk))
        users = self.queryset.filter(company=company)
        serializer = self.serializer_class(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompanyContactOrderViewSet(mixins.CreateModelMixin,
                                 mixins.ListModelMixin,
                                 viewsets.GenericViewSet):
    queryset = CompanyContactOrder.objects.all()
    permission_classes = [IsAuthenticated, HasCompanyAssociated, UserBelongsToCompany]
    serializer_class = CompanyContactOrderSerializer

    def get_queryset(self) -> QuerySet:
        try:
            user = self.request.user
            return CompanyContactOrder.objects.filter(company=user.company)
        except Exception:
            return CompanyContactOrder.objects.none()

    @extend_schema(
        request=CompanyContactOrderRequestSerializer,
        responses={
            status.HTTP_200_OK: ActionStatusSerializer(),
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer()
        }
    )
    def create(self, request, *args, **kwargs):
        company_id = kwargs['company_pk']
        sort_orders = request.data['user_sort_order']
        data = []
        for i in range(len(sort_orders)):
            user_id = sort_orders[i]
            user = User.objects.get(pk=user_id)
            if user.company.id != int(company_id):
                return get_response_from_action_status(
                    http_status=status.HTTP_400_BAD_REQUEST,
                    action_status=ActionStatus(
                        message=f"User ID: {user_id}, does not belong to company {company_id}",
                        status=ActionStatus.Status.ERROR
                    )
                )
            data.append(CompanyContactOrder(sort_order=i, company_id=company_id, user_id=sort_orders[i]))
        sort_order_qs = self.get_queryset().filter(company_id=company_id)
        sort_order_qs.delete()
        self.get_queryset().bulk_create(data)
        return get_response_from_action_status(
            data={'user_sort_order': sort_orders},
            http_status=status.HTTP_200_OK,
            action_status=ActionStatus(
                message='Success',
                status=ActionStatus.Status.SUCCESS
            )
        )


@extend_schema(
    request=GetCompanyByEINRequestSerializer,
    responses={
        status.HTTP_200_OK: CompanySerializer()
    }
)
class GetCompanyByEINView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = GetCompanyByEINRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        ein = serializer.validated_data.get('ein')
        company = get_object_or_404(Company, ein=ein)

        return Response(CompanySerializer(company).data, status=status.HTTP_200_OK)


class CompanyJoinRequestViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CompanyJoinRequest.objects.all()
    serializer_class = CompanyJoinRequestSerializer
    permission_classes = [IsAuthenticated, UserBelongsToCompany]


@extend_schema(
    request=CreateCompanyJoinRequestSerializer,
    responses={
        status.HTTP_200_OK: CompanyJoinRequestSerializer()
    }
)
class CreateCompanyJoinRequestView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = CreateCompanyJoinRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_id = serializer.validated_data.get("company_id")
        company = Company.get_company(company_id)
        company_join_request = CompanyJoinRequest.objects.get_or_create(
            company=company,
            requester=request.user,
            status=CompanyJoinRequest.CompanyJoinRequestStatus.PENDING,
            approver=company.account_owner
        )
        send_company_join_request_email(account_owner=company.account_owner, company_join_request=company_join_request)
        return Response(CompanyJoinRequestSerializer(company_join_request).data, status=status.HTTP_200_OK)


@extend_schema(
    request=ApproveCompanyJoinRequestSerializer,
    responses={
        status.HTTP_200_OK: CompanyJoinRequestSerializer()
    }
)
class ApproveCompanyJoinRequestView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated, IsAccountOwner)
    serializer_class = ApproveCompanyJoinRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_join_request_id = serializer.validated_data.get("company_join_request_id")
        company_join_request = CompanyJoinRequest.objects.get(pk=company_join_request_id)
        company_join_request.status = CompanyJoinRequest.CompanyJoinRequestStatus.APPROVED
        company_join_request.save()
        requester = company_join_request.requester
        requester.company = company_join_request.company
        requester.save()
        return Response()


@extend_schema(
    request=RejectCompanyJoinRequestSerializer,
    responses={
        status.HTTP_200_OK: CompanyJoinRequestSerializer()
    }
)
class RejectCompanyJoinRequestView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated, IsAccountOwner)
    serializer_class = RejectCompanyJoinRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company_join_request_id = serializer.validated_data.get("company_join_request_id")
        company_join_request = CompanyJoinRequest.objects.get(pk=company_join_request_id)
        company_join_request.status = CompanyJoinRequest.CompanyJoinRequestStatus.REJECTED
        company_join_request.save()
        return Response()
