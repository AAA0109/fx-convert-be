from drf_spectacular.utils import extend_schema

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes

from hdlib.DateTime.Date import Date
from hdlib.Utils.Algorithm.filtering import filter_lists

from main.apps.history.services.history_provider import HistoryProvider
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.history.api.v1.serializers.history import *


@extend_schema(
    methods=['post'],
    request=PerformanceRequestSerializer,
    responses={
        status.HTTP_200_OK: PerformanceResponseSerializer
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def performance(request):
    """
    Get the performance of the portfolio or company (hedged values), along with the performance of a hypothetical unhedged
    portfolio with the same cash exposures (unhedged values).
    Returns three lists, a list of "dates", a list of "unhedged_values," and a list of "hedged_values."
    """
    serializer = PerformanceRequestSerializer(data=request.data)
    if not serializer.is_valid(raise_exception=True):
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Request is valid.
    account_id = serializer.validated_data.get("account_id")
    start_date: Date = serializer.validated_data.get('start_date')
    end_date: Date = serializer.validated_data.get('end_date')
    if account_id is not None:
        performance = HistoryProvider().get_account_performance(account=account_id,
                                                                start_date=start_date,
                                                                end_date=end_date)
        times, (hedged, unhedged, pnl, num_cashflows) = filter_lists(performance["times"], [
            performance["hedged"],
            performance["unhedged"],
            performance["pnl"],
            performance["num_cashflows"],
        ])
        return Response(
            {"times": times, "hedged": hedged, "unhedged": unhedged, "pnl": pnl, "num_cashflows": num_cashflows},
            status=status.HTTP_200_OK)
    else:
        company_id = request.user.company.pk
        is_live: bool = serializer.validated_data.get('is_live')
        performance = HistoryProvider().get_total_account_performances(company=company_id,
                                                                       start_date=start_date,
                                                                       end_date=end_date)
        if is_live:
            times, (hedged, unhedged, pnl, num_cashflows) = filter_lists(performance["times"], [
                performance["live_hedged"],
                performance["live_unhedged"],
                performance["live_pnl"],
                performance["live_num_cashflows"],
            ])
            return Response({
                "times": times,
                "hedged": hedged,
                "unhedged": unhedged,
                "pnl": pnl,
                "num_cashflows": num_cashflows,
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "times": performance["times"],
                "hedged": performance["demo_hedged"],
                "unhedged": performance["demo_unhedged"],
                "pnl": performance["delta_demo_pnl"],
                "num_cashflows": performance["demo_num_cashflows"],
            }, status=status.HTTP_200_OK)


@extend_schema(
    methods=['post'],
    request=AccountPnLRequest,
    responses={
        status.HTTP_200_OK: AccountPnLResponse
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def account_pnls(request):
    """
    Get the NPV of a cashflow, the NPV of the account it is part of, and NPV of the company.
    """
    serializer = AccountPnLRequest(data=request.data)
    if not serializer.is_valid(raise_exception=True):
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Request is valid.
    account_id = serializer.validated_data.get("account_id")
    start_date: Date = serializer.validated_data.get('start_date')
    end_date: Date = serializer.validated_data.get('end_date')

    response = HistoryProvider().get_account_pnl(account=account_id,
                                                 start_date=start_date,
                                                 end_date=end_date)
    return Response(response, status=status.HTTP_200_OK)
