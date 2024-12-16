import numpy as np
from drf_spectacular.utils import extend_schema
from hdlib.DateTime.Date import Date
from hdlib.DateTime.DayCounter import DayCounter_HD
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.history.api.v1.serializers.history import *
from main.apps.history.services.history_provider import HistoryProvider
from main.apps.history.services.snapshot_provider import SnapshotProvider


@extend_schema(
    methods=['post'],
    request=RealizedVolatilityRequest,
    responses={
        status.HTTP_200_OK: RealizedVolatilityResponse
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def realized_volatility(request):
    serializer = RealizedVolatilityRequest(data=request.data)
    if not serializer.is_valid(raise_exception=True):
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Request is valid.
    account_id = serializer.validated_data.get("account_id")
    start_date: Date = serializer.validated_data.get('start_date')
    end_date: Date = serializer.validated_data.get('end_date')

    if account_id:
        times, hedged_vol, unhedged_vol = SnapshotProvider().get_cumulative_volatility_ts(account=account_id,
                                                                                          start_date=start_date,
                                                                                          end_date=end_date)
    else:
        company_id = request.user.company.pk

        performance = HistoryProvider().get_total_account_performances(company=company_id,
                                                                       start_date=start_date,
                                                                       end_date=end_date)
        times = performance["times"]
        value_hedged = performance["live_hedged"]
        value_unhedged = performance["live_unhedged"]

        dc = DayCounter_HD()

        hedged_w, unhedged_w = 0., 0.
        hedged_vol, unhedged_vol = [0.], [0.]
        for i in range(1, len(times)):
            dt = dc.year_fraction(start=times[i - 1], end=times[i])
            if dt == 0:
                hedged_vol.append(hedged_vol[-1])
                unhedged_vol.append(unhedged_vol[-1])
                continue
            hedged_dw = np.square(value_hedged[i] - value_hedged[i - 1]) / dt
            unhedged_dw = np.square(value_unhedged[i] - value_unhedged[i - 1]) / dt

            hedged_w += hedged_dw
            unhedged_w += unhedged_dw

            hedged_vol.append(np.sqrt(hedged_w))
            unhedged_vol.append(np.sqrt(unhedged_w))

    response = {
        "times": times,
        "unhedged_realized_vol": unhedged_vol,
        "hedged_realized_vol": hedged_vol,
    }
    return Response(response, status=status.HTTP_200_OK)
