import logging
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from main.apps.core.utils.api import HasCompanyAssociated
from main.apps.marketdata.services.market_liqudity import MarketLiquidity
from main.apps.oems.api.serializers.liquidity import MarketsLiquidityResponse
from main.apps.payment.services.error_utils import PaymentResponseUtils

logger = logging.getLogger(__name__)


class MarketLiquidityAPIView(APIView):
    permission_classes = [IsAuthenticated, HasCompanyAssociated]

    @extend_schema(
        description="Get company's configured pairs liquidity",
        responses={
            status.HTTP_200_OK: MarketsLiquidityResponse
        }
    )
    def get(self, request):

        try:
            market_liquidity_svc = MarketLiquidity(company=request.user.company)
            liquidities = market_liquidity_svc.populate_market_liquidity()
            resp_data =  MarketsLiquidityResponse({'data':liquidities})
            return Response(resp_data.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e, exc_info=True)
            error_resp = PaymentResponseUtils().create_traceback_response(e=e)
            return Response(error_resp, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
