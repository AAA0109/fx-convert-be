import logging
from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from main.apps.oems.api.serializers.liquidity import (
    LiquidityInsightRequestSerializer,
    LiquidityInsightResponseSerializer
)
from main.apps.oems.services.liquidity import CurrencyInsightService
from main.apps.payment.services.error_utils import PaymentResponseUtils


class LiquidityInsightApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LiquidityInsightRequestSerializer,
        responses={
            status.HTTP_200_OK: LiquidityInsightResponseSerializer
        }
    )

    def post(self, request: Request, *args, **kwargs):
        serializer = LiquidityInsightRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            currency_insight_svc = CurrencyInsightService(**serializer.validated_data)
            insight = currency_insight_svc.get_liquidity_insight()
            resp_serializer = LiquidityInsightResponseSerializer(insight)
            return Response(resp_serializer.data, status.HTTP_200_OK)
        except Exception as e:
            logging.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
