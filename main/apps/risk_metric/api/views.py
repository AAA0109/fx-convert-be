import logging
import traceback
import uuid
from typing import Sequence, Optional, Dict

from django.conf import settings
import numpy as np
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from hdlib.DateTime.Date import Date
from hdlib.Instrument.CashFlow import CashFlow as CashflowHDL
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.account.models import Account, DraftCashFlow, CashFlow
from main.apps.billing.services.what_if import FeeWhatIfService, FeeDetail
from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.currency.models import Currency, CurrencyTypes
from main.apps.hedge.models import HedgeSettings
from main.apps.hedge.services.roll_cost_what_if import RollCostWhatIfService, RollCostDetail
from main.apps.margin.services.margin_service import service as margin_service
from main.apps.margin.services.what_if import DefaultWhatIfMarginInterface
from main.apps.marketdata.models import FxTypes
from main.apps.marketdata.services.universe_provider import UniverseProviderService
from main.apps.risk_metric.api.serializers.margin import (
    MarginAndFeeRequest, MarginAndFeesResponse, MarginHealthResponse, MarginHealthRequest)
from main.apps.risk_metric.api.serializers.services.cashflow_risk_provider import (
    GetCashflowRiskConeSerializer, GetCashflowRiskConeResponseSerializer, GetSingleFxPairRiskConeSerializer)
from main.apps.risk_metric.services.cashflow_risk_provider import CashFlowRiskService, FxRiskService

logger = logging.getLogger(__name__)
universe_provider = UniverseProviderService()
what_if_service = DefaultWhatIfMarginInterface()


def valid_drafts_request(account: Optional[Account], drafts: Sequence[DraftCashFlow]) -> bool:
    if account:
        for draft in drafts:
            if draft.account is not None:
                return False
    else:
        for draft in drafts:
            if not draft.cf_draft.exists():
                return False
    return True


class CashFlowRiskApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None)
    def post(self, request: Request, *args, **kwargs):
        """ Get all currency definitions """

        try:
            date = Date.from_str(request.query_params.get('date'), '%Y-%m-%d')
            account_id = request.query_params.get('account_id')

        except Exception:
            return Response({"message": "Must supply date and account_id"}, status=status.HTTP_400_BAD_REQUEST)

        metrics, pnl = CashFlowRiskService().get_simulated_risk_for_account(
            date=date, account=account_id)

        data = metrics.to_dict(pnl=pnl.tolist())
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(methods=['post'], parameters=[
    OpenApiParameter("account_id", OpenApiTypes.INT,
                     OpenApiParameter.QUERY, required=False)
], request=GetCashflowRiskConeSerializer,
    responses=GetCashflowRiskConeResponseSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def get_cashflow_risk_cones_view(request):
    account_id = request.query_params.get('account_id', None)
    if account_id is not None:
        account_id = int(account_id)

    serializer = GetCashflowRiskConeSerializer(data=request.data)
    if serializer.is_valid():
        domestic: CurrencyTypes = serializer.validated_data.get(
            'domestic', None)
        start_date: Date = serializer.validated_data.get('start_date')
        end_date: Date = serializer.validated_data.get('end_date')
        std_dev_levels = serializer.validated_data.get('std_dev_levels')
        do_std_dev_cones = serializer.validated_data.get('do_std_dev_cones')
        risk_reductions: Optional[Sequence[float]] = serializer.validated_data.get(
            'risk_reductions', (0.0,))
        max_horizon: int = serializer.validated_data.get('max_horizon', np.inf)
        cashflows: Dict[Currency, Sequence[CashflowHDL]
                        ] = serializer.validated_data.get('cashflows')
        lower_risk_bound_percent = serializer.validated_data.get(
            'lower_risk_bound_percent')
        upper_risk_bound_percent = serializer.validated_data.get(
            'upper_risk_bound_percent')
        try:
            cones = CashFlowRiskService().get_cashflow_risk_cones(
                domestic=domestic,
                cashflows=cashflows,
                start_date=start_date,
                end_date=end_date,
                risk_reductions=risk_reductions,
                std_dev_levels=std_dev_levels,
                do_std_dev_cones=do_std_dev_cones,
                lower_risk_bound_percent=lower_risk_bound_percent,
                upper_risk_bound_percent=upper_risk_bound_percent,
                max_horizon=max_horizon,
                account=account_id
            )
            return Response(cones, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting cashflow risk cones: {e}")
            logger.exception(e)
            message = {"message": "Unable to compute cashflow risk cones"}
            if settings.DEBUG:
                message["traceback"] = traceback.format_exc()
            return Response(message, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['post'], request=GetCashflowRiskConeSerializer,
               responses=GetCashflowRiskConeResponseSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated, ])
def get_single_fx_risk_cones_view(request):
    serializer = GetSingleFxPairRiskConeSerializer(data=request.data)
    if serializer.is_valid():
        fx_pair: FxTypes = serializer.validated_data.get('fx_pair', None)
        start_date: Date = serializer.validated_data.get('start_date')
        end_date: Date = serializer.validated_data.get('end_date')
        std_dev_levels = serializer.validated_data.get('std_dev_levels')
        do_std_dev_cones = serializer.validated_data.get('do_std_dev_cones')
        cones = FxRiskService().get_single_fx_risk_cones(
            fx_pair=fx_pair,
            start_date=start_date,
            end_date=end_date,
            std_dev_levels=std_dev_levels,
            do_std_dev_cones=do_std_dev_cones,
        )
        return Response(cones, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['post'], request=MarginAndFeeRequest, responses=MarginAndFeesResponse)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def get_margin_and_fee_view(request):
    """
    Get the margin and fee for a given account.

    The request includes a draft ID. If the draft is associated with a live cashflow then it is treated as an edit
    to an existing cashflow. Otherwise, it is treated as a new cashflow.

    If the cashflow is an existing one, then the account id should be left empty.
    If the cashflow is a new one then you must specify an account id to get back the margin update.
    """
    date = Date.today()
    serializer = MarginAndFeeRequest(data=request.data)
    serializer.is_valid(raise_exception=True)

    company = request.user.company
    cashflows = list(CashFlow.get_company_active_cashflows(company))
    deleted_cashflows = serializer.validated_data.get(
        'deleted_cashflow_ids', [])
    cashflows = list(
        filter(lambda cf: cf.id not in deleted_cashflows, cashflows))
    drafts = DraftCashFlow.objects.filter(
        id__in=serializer.validated_data.get('draft_ids', []))
    account_id = serializer.validated_data.get('account_id', None)
    hedge_settings = serializer.validated_data.get('hedge_settings', None)

    if account_id:
        # Explicitly set hedge setting to null as a defensive measure
        # because later on we use that to determine if the account needs
        # to be deleted on or not
        hedge_settings = None
        account = Account.get_account(account=account_id)
    elif hedge_settings:

        account = Account.create_account(name=uuid.uuid4().hex,
                                         company=company,
                                         account_type=Account.AccountType.LIVE,
                                         is_active=True,
                                         is_hidden=True)
        try:
            hedge_settings, _ = HedgeSettings.create_or_update_settings(
                account=account,
                margin_budget=hedge_settings.get('margin_budget', 2.e10),
                method=hedge_settings.get("method", "MIN_VAR"),
                max_horizon_days=hedge_settings.get(
                    "max_horizon_days", 365 * 20),
                custom={
                    'VolTargetReduction': hedge_settings.get("custom").get("vol_target_reduction"),
                    'VaR95ExposureRatio': hedge_settings.get("custom").get("var_95_exposure_ratio", None),
                    'VaR95ExposureWindow': hedge_settings.get("custom").get("var_95_exposure_window", None)
                })
        except Exception as e:
            logger.error("Error creating hedge settings: %s", e)
            # make sure to delete the account if we encounter an exception here.
            account.delete()
    else:
        account = None

    new_cfs = []
    try:
        if account:
            new_cfs = [draft.to_cashflow() for draft in drafts]

            for cf in new_cfs:
                if not hasattr(cf, 'account'):
                    cf.account = account
                cashflows.append(cf)
        else:
            for draft in drafts:
                cf = draft.cf_draft.first()
                cf.update_from_draft(draft)
                new_cfs.append(cf)

        margin_detail = margin_service.get_margin_detail(
            company=company, date=date)

        spot_cache = what_if_service.fx_spot_provider.get_spot_cache(
            window=30, time=date)

        old_new_positions = what_if_service.get_position_changes_what_if_after_trades(
            date=date,
            company=company,
            new_cashflows=cashflows,
            account_type=Account.AccountType.LIVE,
            spot_fx_cache=spot_cache)

        margin_detail_new = what_if_service.compute_margin_for_position(
            old_new_positions=old_new_positions, date=date, company=company, spot_fx_cache=spot_cache
        )

        try:
            # TODO: convert this to raise exception after more testing
            fee_what_if = FeeWhatIfService()
            fee_detail = fee_what_if.get_fee_details_what_if_after_new_cashflows(date=date, company=company,
                                                                                 new_cashflows=new_cfs,
                                                                                 spot_fx_cache=spot_cache)
        except Exception as e:
            logger.error("Error computing what if fees: %s", e)
            fee_detail = FeeDetail.new_all_zeros()
        try:
            roll_what_if = RollCostWhatIfService()
            roll_detail = roll_what_if.get_roll_cost_estimate_what_if_after_trades(date=date,
                                                                                   company=company,
                                                                                   new_cashflows=new_cfs,
                                                                                   spot_fx_cache=spot_cache)
            target_reduction = hedge_settings.custom.get("VolTargetReduction") if hedge_settings \
                else account.hedge_settings.custom.get("VolTargetReduction")
            if target_reduction is None:
                logger.error(
                    'Error retrieving vol target reduction, setting to 100%')
                target_reduction = 1.
            else:
                logger.debug(
                    f"Target reduction for what if roll calc: {100 * target_reduction}%")

            # NOTE: this a poor mans version, avoids computing hedge cost.
            # its a first order approx... b/c what do I do if I compute the hedge, and the change in roll cost turns
            # out to be negative? but only for one day b/c then a cashflow rolls off
            # the problem is that we need to estimate the cost for adding a new cashflow, and the only proper way to do
            # this is to walk forward the full set of positions and hedge every day in future, calculating the roll
            # cost each day. so instead, we just treat the cashflow in isolation, and say that approximately it will
            # add that much cost, to avoid the issues of netting etc.
            roll_detail.cost_total *= target_reduction

            if roll_detail.cashflow_total != fee_detail.cashflow_total:
                logger.error("There is an inconsistency between the calculated cashflows between roll and fees,"
                             f"     this needs to be investigated:"
                             f"     roll_detail.cashflow_total = {roll_detail.cashflow_total}"
                             f"     fee_detail.cashflow_total = {fee_detail.cashflow_total}")

        except Exception as e:
            logger.error("Error computing what if roll cost: %s", e)
            roll_detail = RollCostDetail.new_all_zeros()

        # Compute combined / total cost and relative to cashflow
        cashflow_total = fee_detail.cashflow_total
        cost_total = fee_detail.cost_total + roll_detail.cost_total
        cost_proportion = cost_total / cashflow_total if cashflow_total > 0 else 0
        margin_and_fee_response = {
            "margin_required": margin_detail_new.margin_requirement if margin_detail_new.excess_liquidity <= 0.0 else 0.0,
            # note that the definition of margin is not very clear, so currently it is defined as excess liquidity before
            # the new trades - margin required.
            "margin_available": margin_detail.excess_liquidity,
            "cashflow_total_value": cashflow_total,
            "last_maturity_days": fee_detail.maturity_days,
            "num_cashflows": fee_detail.num_cashflows,
            "previous_daily_aum": fee_detail.previous_daily_aum,
            "previous_rolling_aum": fee_detail.previous_rolling_aum,
            "fee_detail": {
                "update_fee_amount": fee_detail.new_cashflow_fee,
                "update_fee_percentage": fee_detail.new_cashflow_fee_rate,
                "hold_fee_amount": fee_detail.aum_total_fee,
                "hold_fee_percentage": fee_detail.aum_fee_rate_of_cashflows,
                "cashflow_update_fee_at_close_amount": -123456,  # TODO: remove this field
                "cashflow_update_fee_at_close_percent": -0.12,  # TODO: remove this field
                "max_hedge_cost": -123456,  # TODO: remove this field,
                "roll_cost_amount": roll_detail.cost_total,
                "roll_cost_percentage": roll_detail.roll_cost_proportion_of_cashflows
            },
            "fee_details": {
                "totals": {
                    "name": "Estimated Hedge Cost",
                    "amount": cost_total,
                    "rate": cost_proportion
                },
                "fee_groups": [
                    {
                        "name": "Pangea's Fees",
                        "fees": [
                            {
                                "name": "Pangea hedge fee",
                                "amount": fee_detail.new_cashflow_fee,
                                "rate": fee_detail.new_cashflow_fee_rate
                            },
                            {
                                "name": "Annualized advisory fee",
                                "amount": fee_detail.aum_total_fee,
                                "rate": fee_detail.aum_fee_rate
                            }
                        ]
                    },
                    {
                        "name": "Market Costs",
                        "fees": [
                            {
                                "name": "Spot market fee",
                                "amount": roll_detail.cost_total,
                                "rate": roll_detail.roll_cost_proportion_of_cashflows
                            }
                        ]
                    }
                ]
            }
        }
        margin_and_fee = MarginAndFeesResponse(margin_and_fee_response)
        return Response(margin_and_fee.data, status=status.HTTP_200_OK)
    finally:
        if hedge_settings:
            hedge_settings.delete()
            account.delete()


@extend_schema(methods=['post'], request=MarginHealthRequest, responses=MarginHealthResponse)
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasCompanyAssociated])
def get_margin_health_report(request):
    """
    Get the margin health report for a given company.
    """
    serializer = MarginHealthRequest(data=request.data)
    serializer.is_valid(raise_exception=True)
    report = margin_service.get_margin_health_report(company=request.user.company,
                                                     custom_amount=serializer.validated_data.get('custom_amount',
                                                                                                 None))

    date = Date.today()
    serializer = MarginHealthResponse({
        "margin_balance": report.margin_detail.excess_liquidity,
        "recommended_deposit": report.recommended_deposit,
        "recommended_withdrawl": report.recommended_withdrawl,
        "minimum_deposit": report.minimum_deposit,
        "minimum_withdrawl": report.maximum_withdrawl,

        "ach_deposit_date": date + 3,
        "wire_deposit_date": date + 3,
        "margins": [
            {
                "date": mp.date,
                "amount": mp.amount_before_deposit,
                "health_score": bm.health_score(),
                "health_score_after_deposit": mp.health_score_after_deposit(),
                "health_score_hypothetical": mt.health_score_after_deposit(),
                "total_hedging": mp.total_hedge
            } for (bm, mt, mp) in zip(report.baseline_margin,
                                      report.projected_margins_theoretical,
                                      report.projected_margins_pending)],
        "deposit_history": [
            {
                "date": Date.create(2020, 1, 1),
                "amount": 18000,
                "currency": "USD"
            }
        ]

    })
    return Response(serializer.data, status=status.HTTP_200_OK)
