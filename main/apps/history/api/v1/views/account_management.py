from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from hdlib.DateTime.Date import Date

from main.apps.history.api.v1.serializers.account_management import (
    HistoryRequestSerializer,
    ActivitiesSerializer,
    FeesPaymentsSerializer,
    BankStatementsSerializer,
    TradesSerializer
)
from main.apps.core.serializers.action_status_serializer import ActionStatusSerializer
from main.apps.currency.models import Currency


class ActivitiesView(GenericAPIView):
    serializer_class = ActivitiesSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        if self.request.version == 'v1':
            return {
                "activities": [
                    {
                        "description": "Reset login permissions",
                        "date": Date(2022, 7, 5)
                    },
                    {
                        "description": "Permissions set",
                        "date": Date(2022, 7, 4)
                    },
                    {
                        "description": "User added",
                        "date": Date(2022, 7, 4)
                    },
                    {
                        "description": "Margin account verified",
                        "date": Date(2022, 7, 2)
                    },
                    {
                        "description": "Company verified",
                        "date": Date(2022, 7, 1)
                    },
                    {
                        "description": "IB application approved",
                        "date": Date(2022, 6, 28)
                    },
                    {
                        "description": "Account created",
                        "date": Date(2022, 6, 24)
                    }
                ]
            }
        else:
            return super().get_object()

    @extend_schema(
        parameters=[
            HistoryRequestSerializer
        ],
        request=HistoryRequestSerializer,
        responses={
            status.HTTP_200_OK: ActivitiesSerializer,
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer
        }
    )
    def get(self, request):
        activities = ActivitiesSerializer(self.get_object())
        return Response(activities.data, status=status.HTTP_200_OK)


class FeesPaymentsView(GenericAPIView):
    serializer_class = FeesPaymentsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return {
            "fees_and_payments": [
                {
                    "description": "New Hedge",
                    "account_hedge_request_id": 111,
                    "amount": 4000,
                    "date": Date(2022, 6, 28)
                },
                {
                    "description": "Fee: Hedge increase",
                    "account_hedge_request_id": 111,
                    "amount": 2000,
                    "date": Date(2022, 5, 12)
                },
                {
                    "description": "Fee adjustment",
                    "account_hedge_request_id": 111,
                    "amount": 4000,
                    "date": Date(2022, 4, 12)
                },
                {
                    "description": "Payment received",
                    "account_hedge_request_id": 111,
                    "amount": -4000,
                    "date": Date(2022, 6, 28)
                },
                {
                    "description": "Jul. Maintenance Fee",
                    "account_hedge_request_id": None,
                    "amount": 4000,
                    "date": Date(2022, 6, 28)
                },
                {
                    "description": "New cashflow",
                    "account_hedge_request_id": 111,
                    "amount": 2000,
                    "date": Date(2022, 6, 28)
                }
            ]
        }

    @extend_schema(
        parameters=[
            HistoryRequestSerializer
        ],
        request=HistoryRequestSerializer,
        responses={
            status.HTTP_200_OK: FeesPaymentsSerializer,
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer
        }
    )
    def get(self, request):
        fees_payments = FeesPaymentsSerializer(self.get_object())
        return Response(fees_payments.data, status=status.HTTP_200_OK)


class BankStatementsView(GenericAPIView):
    serializer_class = BankStatementsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return {
            'statements': [
                {
                    'description': "Margin deposit",
                    "amount": 4000,
                    "account": "6844",
                    "draft": 1559,
                    "date": Date(2022, 6, 28)
                },
                {
                    'description': "Margin withdrawal",
                    "amount": -4000,
                    "account": "6844",
                    "draft": 1559,
                    "date": Date(2022, 5, 12)
                },
                {
                    'description': "Margin deposit",
                    "amount": 4000,
                    "account": "6844",
                    "draft": 1559,
                    "date": Date(2022, 4, 12)
                },
                {
                    'description': "Margin withdrawal",
                    "amount": -2000,
                    "account": "6844",
                    "draft": 1559,
                    "date": Date(2022, 3, 23)
                }
            ]
        }

    @extend_schema(
        parameters=[
            HistoryRequestSerializer
        ],
        request=BankStatementsSerializer,
        responses={
            status.HTTP_200_OK: BankStatementsSerializer,
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer
        }
    )
    def get(self, request):
        banking_statements = BankStatementsSerializer(self.get_object())
        return Response(banking_statements.data, status=status.HTTP_200_OK)


class TradesView(GenericAPIView):
    serializer_class = TradesSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return {
            "trades": [
                {
                    "currency": Currency.get_currency('JPY'),
                    "units": 288888888,
                    "price": 0.00734,
                    "date": Date(2022, 7, 3)
                },
                {
                    "currency": Currency.get_currency('CAD'),
                    "units": -20000000,
                    "price": 0.7757,
                    "date": Date(2022, 7, 4)
                },
                {
                    "currency": Currency.get_currency('JPY'),
                    "units": 288888888,
                    "price": 0.00722,
                    "date": Date(2022, 6, 28)
                },
                {
                    "currency": Currency.get_currency('CAD'),
                    "units": -20000000,
                    "price": 0.7653,
                    "date": Date(2022, 5, 15)
                }
            ]
        }

    @extend_schema(
        parameters=[
            HistoryRequestSerializer
        ],
        request=HistoryRequestSerializer,
        responses={
            status.HTTP_200_OK: TradesSerializer,
            status.HTTP_400_BAD_REQUEST: ActionStatusSerializer
        }
    )
    def get(self, request):
        trades = TradesSerializer(self.get_object())
        return Response(trades.data, status=status.HTTP_200_OK)
