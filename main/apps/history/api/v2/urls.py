from django.urls import path, include
from rest_framework import routers
from main.apps.history.api.v1.views.performance import performance, account_pnls
from main.apps.history.api.v1.views.cashflow_weight import cashflow_weight
from main.apps.history.api.v1.views.realized_volatility import realized_volatility
from main.apps.history.api.v1.views.cashflow_abs_forward import cashflow_abs_forward

from main.apps.history.api.v2.views.account_management import (
    ActivitiesView as ActivitiesViewV2,
    FeesPaymentsView as FeesPaymentViewV2,
    BankStatementsView as BankStatementsViewV2,
    TradesView as TradesViewV2
)
app_name = 'history'
router_v2 = routers.DefaultRouter()
router_v2.register(r'fees-payments', FeesPaymentViewV2, basename='fees-payments')
router_v2.register(r'bank-statements', BankStatementsViewV2, basename='bank-statements')
router_v2.register('trades', TradesViewV2, basename='trades')
router_v2.register('activities', ActivitiesViewV2, basename='activities')
urlpatterns = [
    path('', include(router_v2.urls)),
    path('cashflow_weight/', cashflow_weight, name='cashflow-weight'),
    path('performance/', performance, name='performance'),
    path('account_pnls', account_pnls, name="account-pnls"),
    path('realized_volatility/', realized_volatility, name='realized-volatility'),
    path('cashflow_abs_forward/', cashflow_abs_forward, name='cashflow-abs-forward'),
]
