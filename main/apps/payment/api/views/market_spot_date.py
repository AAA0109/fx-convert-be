import logging
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from main.apps.payment.api.serializers.market_spot_date import (
    MarketSpotDateRequestSerializer,
    MarketSpotDatesSerializer
)
from main.apps.payment.services.error_utils import PaymentResponseUtils
from main.apps.payment.services.market_spot_date import MarketSpotDateProvider

logger = logging.getLogger(__name__)


class MarketSpotDateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Get spot dates from provided market/pair list",
        request=MarketSpotDateRequestSerializer,
        responses={
            status.HTTP_200_OK: MarketSpotDatesSerializer
        }
    )
    def post(self, request):
        serializer = MarketSpotDateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            market_spot_date_svc = MarketSpotDateProvider()
            spot_dates = market_spot_date_svc.populate_pairs_spot_dates(
                pairs=serializer.validated_data)
            resp_data =  MarketSpotDatesSerializer(spot_dates)
            return Response(resp_data.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
