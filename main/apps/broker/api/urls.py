from django.urls import path, re_path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter

from main.apps.broker.api.views.market_universe import CompanyMarketUniverse
from main.apps.broker.api.views.broker_events import BrokerEventsView
from main.settings.base import API_SCOPE

app_name = 'broker'

if API_SCOPE == 'internal':
    router = routers.DefaultRouter()
    urlpatterns = [
        path('', include(router.urls)),
        path('universe/', CompanyMarketUniverse.as_view(), name='universe'),
        path("<slug:broker>/<slug:action>", BrokerEventsView.as_view() )
    ]
