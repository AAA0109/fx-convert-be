from django.urls import path, include

from main.settings.base import API_SCOPE

urlpatterns = [
    path('cashflow/', include('main.apps.cashflow.api.urls')),
    path('settlement/', include('main.apps.settlement.api.urls')),
    path('oems/', include('main.apps.oems.api.urls')),
    path('marketdata/', include('main.apps.marketdata.api.urls')),
    path('webhook/', include('main.apps.webhook.api.urls')),
    path('healthcheck/', include('health_check.urls')),
]

if API_SCOPE == 'internal':
    urlpatterns += [
        path('', include('main.apps.account.api.urls')),
        path('auth/', include('main.apps.auth.api.urls')),
        path('currency/', include('main.apps.currency.api.urls')),
        path('country/', include('main.apps.country.api.urls')),
        path('risk/', include('main.apps.risk_metric.api.urls')),
        path('hedge/', include('main.apps.hedge.api.urls')),
        path('payments/', include('main.apps.payment.api.urls')),
        path('notification/', include('main.apps.notification.api.urls')),
        path('broker/', include('main.apps.ibkr.api.urls')),
        path('broker/', include('main.apps.corpay.api.urls')),
        path('token/', include('main.apps.auth.urls')),
        # path('healthcheck/', include('health_check.urls')),
        path('marketing/', include('main.apps.marketing.api.urls')),
        path('ndl/', include('main.apps.ndl.api.urls')),
        path('dataprovider/', include('main.apps.dataprovider.api.urls')),
        path('broker/', include('main.apps.broker.api.urls')),
        path('slack/', include('main.apps.slack.api.urls')),
        path('approval/', include('main.apps.approval.api.urls')),
    ]


