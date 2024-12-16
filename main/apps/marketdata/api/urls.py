from django.urls import path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter

from main.apps.marketdata.api.views.corpay import FxSpotCorpayApiViewSet, FxForwardCorpayApiViewSet
from main.apps.marketdata.api.views.fx import (
    FxSpotIntraAverageApiView,
    FxSpotApiView,
    FxSpotIntraApiView,
    FxForwardApiView,
    TradingCalendarApiView, P10FxPairView
)
from main.apps.marketdata.api.views.future import (
    FutureIntraApiView,
    FutureLiquidHoursApiView,
    FutureTradingHoursApiView
)

from main.apps.marketdata.api.views.index import IndexApiView
from main.apps.marketdata.api.views.initial import (
    InitialMarketStateApiView,
    RecentRateApiView,
    HistoricalRateApiView,
    RecentVolApiView
)
from main.apps.marketdata.api.views.market_liquidity import MarketLiquidityAPIView
from main.settings.base import API_SCOPE

app_name = 'marketdata'

router = routers.DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('recent-rate/', RecentRateApiView.as_view(), name='recent-market-rate'),
    path('historical-rates/', HistoricalRateApiView.as_view(), name='historical-market-rates'),
    path('risk/', RecentVolApiView.as_view(), name='risk'),
]

if API_SCOPE == 'internal':

    spot_router = routers.DefaultRouter()
    spot_router.register(r'corpay', FxSpotCorpayApiViewSet, basename='spot-corpay')
    forward_router = routers.DefaultRouter()
    forward_router.register(r'corpay', FxForwardCorpayApiViewSet, basename='forward-corpay')

    urlpatterns += [
        path('spot/', FxSpotApiView.as_view(), name='spot-list'),
        path('spot/intra/', FxSpotIntraApiView.as_view(), name='spot-intra-list'),
        path('spot/', include(spot_router.urls)),
        path('forwards/', FxForwardApiView.as_view(), name='forwards-list'),
        path('forwards/', include(forward_router.urls)),
        path('trading_calendar/', TradingCalendarApiView.as_view(), name='trading-calendar-list'),
        path('spot/intra/average/', FxSpotIntraAverageApiView.as_view(), name='spot-intra-average'),
        path('fxPair/p10/', P10FxPairView.as_view(), name='p10-fxpair'),
        path('future/intra/', FutureIntraApiView.as_view(), name='future-intra-list'),
        path('future/liquid_hours/', FutureLiquidHoursApiView.as_view(), name='future-liquid-hours'),
        path('future/trading_hours/', FutureTradingHoursApiView.as_view(), name='future-trading-hours'),
        path('asset/index/', IndexApiView.as_view(), name='asset-index-list'),
        path('initial-state/', InitialMarketStateApiView.as_view(), name='initial-market-state'),
        path('markets-liquidity/', MarketLiquidityAPIView.as_view(), name='markets-liquidity')
    ]


