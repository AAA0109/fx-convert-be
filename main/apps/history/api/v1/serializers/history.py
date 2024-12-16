from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from main.apps.core.serializers.common import HDLDateField


# ============================================================
#  PortfolioPerformance
# ============================================================

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Portfolio performance request",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "account_id": 15
            }
        ),
        OpenApiExample(
            "Live company performance request",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "is_live": True
            }
        ),
        OpenApiExample(
            "Demo company performance request",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "is_live": False
            }
        ),
    ])
class PerformanceRequestSerializer(serializers.Serializer):
    """
    An object representing a request to get the portfolio performance.
    """

    start_date = HDLDateField()
    end_date = HDLDateField()
    account_id = serializers.IntegerField(required=False)
    is_live = serializers.BooleanField(required=False, default=True)


class PerformanceResponseSerializer(serializers.Serializer):
    times = serializers.ListSerializer(child=serializers.DateTimeField())
    unhedged = serializers.ListSerializer(child=serializers.FloatField())
    hedged = serializers.ListSerializer(child=serializers.FloatField())
    pnl = serializers.ListSerializer(child=serializers.FloatField())
    num_cashflows = serializers.ListSerializer(child=serializers.IntegerField())

# ============================================================
#  Account PnL
# ============================================================

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Account PnL request",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "account_id": 15
            }
        )
    ])
class AccountPnLRequest(serializers.Serializer):
    """
    An object representing a request to get some account's PnL.
    """
    start_date = HDLDateField()
    end_date = HDLDateField()
    account_id = serializers.IntegerField(required=False)

class AccountPnLResponse(serializers.Serializer):
    times = serializers.ListSerializer(child=serializers.DateTimeField())
    unhedged_pnl = serializers.ListSerializer(child=serializers.FloatField())
    hedged_pnl = serializers.ListSerializer(child=serializers.FloatField())


# ============================================================
#  CompanyPerformance
# ============================================================

class CompanyPerformanceRequest(serializers.Serializer):
    """
    An object representing a request to get the company performance
    """

    start_date = HDLDateField()
    end_date = HDLDateField()
    is_live = serializers.BooleanField()


class CompanyPerformanceResponse(serializers.Serializer):
    times = serializers.ListSerializer(child=serializers.DateTimeField())

    delta_hedged = serializers.ListSerializer(child=serializers.FloatField())
    delta_unhedged = serializers.ListSerializer(child=serializers.FloatField())
    delta_pnl = serializers.ListSerializer(child=serializers.FloatField())


# ============================================================
#  CashFlowWeight
# ============================================================

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "CashFlow weight request",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "cashflow_ids": [1, 2, 15, 17],
            }
        )
    ])
class CashFlowWeightRequest(serializers.Serializer):
    """
    An object representing a request to get the cashflow weight.
    """

    start_date = HDLDateField()
    end_date = HDLDateField()
    # List of cashflow IDs.
    cashflow_ids = serializers.ListSerializer(child=serializers.IntegerField())


class CashFlowWeightResponse(serializers.Serializer):
    times = serializers.ListSerializer(child=serializers.DateTimeField())
    cashflow_npv = serializers.ListSerializer(child=serializers.FloatField())
    account_npv = serializers.ListSerializer(child=serializers.FloatField())
    company_npv = serializers.ListSerializer(child=serializers.FloatField())


# ============================================================
#  RealizedVariance
# ============================================================

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Realized volatility request for an account",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "account_id": 13,
            }
        ),
        OpenApiExample(
            "Realized volatility request for a company",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30"
            }
        )
    ])
class RealizedVolatilityRequest(serializers.Serializer):
    start_date = HDLDateField()
    end_date = HDLDateField()
    account_id = serializers.IntegerField(required=False)
    # If account_id is None, this select whether we want live or demo company realized vol
    is_live = serializers.BooleanField(required=False)


class RealizedVolatilityResponse(serializers.Serializer):
    times = serializers.ListSerializer(child=serializers.DateTimeField())
    unhedged_realized_vol = serializers.ListSerializer(child=serializers.FloatField())
    hedged_realized_vol = serializers.ListSerializer(child=serializers.FloatField())


# ============================================================
#  RealizedVariance
# ============================================================

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Cashflow absolute forward request for an account, id = 13.",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "account_id": 13,
            }
        ),
        OpenApiExample(
            "Cashflow absolute forward request for a company's live accounts.",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "is_live": True
            }
        ),
        OpenApiExample(
            "Cashflow absolute forward request for a company's demo accounts.",
            value={
                "start_date": "2020-01-01",
                "end_date": "2020-01-30",
                "is_live": False
            }
        ),
    ])
class CashflowAbsForwardRequest(serializers.Serializer):
    start_date = HDLDateField()
    end_date = HDLDateField()
    account_id = serializers.IntegerField(required=False)
    is_live = serializers.BooleanField(required=False, default=True)


class CashflowAbsForwardResponse(serializers.Serializer):
    times = serializers.ListSerializer(child=serializers.DateTimeField())
    cashflow_abs_fwd = serializers.ListSerializer(child=serializers.FloatField())
    num_cashflows = serializers.ListSerializer(child=serializers.IntegerField())
