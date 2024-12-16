from typing import List

from drf_spectacular.utils import extend_schema
from requests import Request
from rest_framework import status
from rest_framework.response import Response

from main.apps.account.models import Company
from main.apps.core.api.system import SystemAPIOnlyView


@extend_schema(
    responses={
        status.HTTP_200_OK: List[int]
    }
)
class SupportedCompaniesView(SystemAPIOnlyView):

    def get(self, request: Request, *args, **kwargs):
        """
        List of companies to get account summary for
        """
        companies: List[int] = Company.objects.filter(
            status=Company.CompanyStatus.ACTIVE,
        ).filter(
            broker_accounts__broker__name='IBKR',
            broker_accounts__broker_account_name__isnull=False
        ).values_list('id', flat=True)

        return Response(status=status.HTTP_200_OK, data=companies)
