import numpy as np
from drf_spectacular.utils import extend_schema
from hdlib.DateTime.DayCounter import DayCounter_HD

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes

from hdlib.Instrument.CashFlow import CashFlow as CashFlowHDL
from hdlib.DateTime.Date import Date
from hdlib.Core.FxPair import FxPair as FxPairHDL
from hdlib.Utils.Algorithm.filtering import filter_lists

from main.apps.history.services.history_provider import HistoryProvider
from main.apps.history.services.snapshot_provider import SnapshotProvider
from main.apps.marketdata.services.fx.fx_provider import FxForwardProvider
from main.apps.account.models import Account, CashFlow
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.hedge.models import HedgeSettings
from main.apps.history.api.v1.serializers.history import *


@extend_schema(
    methods=['post'],
    request=CashFlowWeightRequest,
    responses={
        status.HTTP_200_OK: CashFlowWeightResponse
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def cashflow_weight(request):
    """
    Get the NPV of a cashflow, the NPV of the account it is part of, and NPV of the company.
    """
    serializer = CashFlowWeightRequest(data=request.data)
    if not serializer.is_valid(raise_exception=True):
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Request is valid.
    cashflow_ids = serializer.validated_data.get("cashflow_ids")
    start_date: Date = serializer.validated_data.get('start_date')
    end_date: Date = serializer.validated_data.get('end_date')

    # Make sure the cashflow comes from the account.
    cashflows = CashFlow.get_cashflows(cashflow_ids=cashflow_ids)
    if not cashflows:
        raise ValueError("cashflow is invalid or does not belong to the account")
    if len(cashflows) != len(cashflow_ids):
        raise ValueError(f"could not find all cashflows")
    if len(cashflows) == 0:
        raise ValueError(f"cannot run the cashflow weight endpoint with zero cashflows")

    account = Account.get_account(cashflows[0].account)
    times1, account_value = SnapshotProvider().get_account_cashflow_abs_npv_ts(account=account,
                                                                               start_date=start_date,
                                                                               end_date=end_date)
    company = account.company
    times2, company_value = SnapshotProvider().get_company_cashflow_abs_npv_ts(company=company,
                                                                               start_date=start_date,
                                                                               end_date=end_date)

    # Make sure the times align.
    m1 = {time: value for time, value in zip(times1, account_value)}
    m2 = {time: value for time, value in zip(times2, company_value)}
    times, account_value, company_value = [], [], []
    for t in sorted(set(m1.keys()).union((m2.keys()))):
        if t in m1 and t in m2:
            times.append(t)
            account_value.append(m1[t])
            company_value.append(m2[t])

    # Get the time horizon.
    settings = HedgeSettings.get_hedge_settings(account=account)
    max_days = settings.max_horizon_days if settings else 365
    cashflow_cutoff = end_date + max_days

    cashflow_values = []
    for date in times:
        abs_npv = 0.0
        forwards_by_fx = {}
        for cashflow in cashflows:
            pair = FxPairHDL(base=cashflow.currency, quote=company.currency)
            if pair not in forwards_by_fx:
                forwards_by_fx[pair] = FxForwardProvider().get_forward_curve(pair=pair, date=date)
            forward_curve = forwards_by_fx[pair]
            for cf in cashflow.get_hdl_cashflows():
                if date <= cf.pay_date < cashflow_cutoff:
                    cf: CashFlowHDL = cf
                    abs_npv += np.abs(cf.amount * forward_curve.at_D(date=cf.pay_date))
        cashflow_values.append(abs_npv)

    response = {
        "times": times,
        "cashflow_npv": cashflow_values,
        "account_npv": account_value,
        "company_npv": company_value,
    }
    return Response(response, status=status.HTTP_200_OK)
