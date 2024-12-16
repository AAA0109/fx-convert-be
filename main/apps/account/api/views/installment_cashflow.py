from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from main.apps.account.api.serializers.installment import InstallmentSerializer
from main.apps.account.api.services.customer import CustomerAPIService
from main.apps.core.utils.api import *


class InstallmentViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]
    queryset = InstallmentCashflow.objects.all()
    serializer_class = InstallmentSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    def get_queryset(self):
        return InstallmentCashflow.objects.filter(company=self.request.user.company)

    @extend_schema(
        responses={
            status.HTTP_200_OK: InstallmentSerializer(many=True)
        }
    )
    def list(self, request):
        """
        Get all the recurring cashflow for an account
        """
        cashflows = self.get_queryset()
        serializer = InstallmentSerializer(cashflows, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=InstallmentSerializer,
        responses={
            status.HTTP_201_CREATED: InstallmentSerializer,
        }
    )
    def create(self, request):
        """
        Add a recurring cashflow for an account
        """
        serializer = InstallmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        installment = CustomerAPIService().create_installment(
            company=request.user.company,

            name=serializer.data['installment_name'])

        serializer = InstallmentSerializer(installment)
        data = serializer.data
        return Response(data, status.HTTP_201_CREATED)

    @extend_schema(
        request=InstallmentSerializer,
        responses={
            status.HTTP_200_OK: InstallmentSerializer,
        }
    )
    def retrieve(self, request, pk: int):
        """
        Get a recurring cashflow by id
        """
        installment = get_object_or_404(self.get_queryset(), pk=int(pk))
        serializer = InstallmentSerializer(installment)
        return Response(serializer.data)

    def update(self, request, pk: int):
        """
        Replace an existing recurring cashflow with a new one, effectively 'updating' or 'editing' a cashflow

        The cashflow must have the same name as an existing cashflow, which it is editing. The name must not be None.
        """

        # IsAccountValidated makes sure account_id is valid
        installment = get_object_or_404(self.get_queryset(), pk=int(pk))

        serializer = InstallmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        installment = CustomerAPIService().edit_installment(
            installment_id=installment,
            company_id=self.request.user.company,

            name=serializer.data['installment_name'])

        serializer = InstallmentSerializer(installment)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            status.HTTP_204_NO_CONTENT: None,
        }
    )
    def destroy(self, request, pk: int):
        """
        Remove a recurring cashflow from an account
        """
        CustomerAPIService().remove_installment(
            company_id=self.request.user.company,

            installment_id=int(pk)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
