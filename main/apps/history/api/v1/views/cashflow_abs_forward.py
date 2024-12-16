from drf_spectacular.utils import extend_schema
from hdlib.DateTime.Date import Date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.history.api.v1.serializers.history import *
from main.apps.history.services.history_provider import HistoryProvider


@extend_schema(
    methods=['post'],
    request=CashflowAbsForwardRequest,
    responses={
        status.HTTP_200_OK: CashflowAbsForwardResponse
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def cashflow_abs_forward(request):
    serializer = CashflowAbsForwardRequest(data=request.data)
    if not serializer.is_valid(raise_exception=True):
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Request is valid.
    account_id = serializer.validated_data.get("account_id")
    start_date: Date = serializer.validated_data.get("start_date")
    end_date: Date = serializer.validated_data.get("end_date")
    is_live: bool = serializer.validated_data.get("is_live")

    company_id = request.user.company.pk
    if account_id is not None:
        # Get the cashflow abs forward for an account.
        fwd = HistoryProvider().get_cashflow_abs_forward(account=account_id,
                                                         start_date=start_date,
                                                         end_date=end_date)
        response = {
            "times": fwd["times"],
            "cashflow_abs_fwd": fwd["cashflow_abs_fwd"],
            "num_cashflows": fwd["num_cashflows"]
        }
    else:
        if is_live is None:
            is_live = True
        # Get the cashflow abs forward for a company.
        fwd = HistoryProvider().get_cashflow_abs_forward(company=company_id,
                                                         start_date=start_date,
                                                         end_date=end_date)
        response = {
            "times": fwd["times"],
            "cashflow_abs_fwd": fwd["live_cashflow_abs_fwd"] if is_live else fwd["demo_cashflow_abs_fwd"],
            "num_cashflows": fwd["live_num_cashflows"] if is_live else fwd["demo_num_cashflows"],
        }

    return Response(response, status=status.HTTP_200_OK)
