from django.urls import path, include
from rest_framework import routers
from rest_framework.versioning import URLPathVersioning

from main.apps.history.api.v1.views.account_management import (
    ActivitiesView,
    FeesPaymentsView,
    BankStatementsView,
    TradesView
)
from main.apps.history.api.v1.views.performance import performance, account_pnls
from main.apps.history.api.v1.views.cashflow_weight import cashflow_weight
from main.apps.history.api.v1.views.realized_volatility import realized_volatility
from main.apps.history.api.v1.views.cashflow_abs_forward import cashflow_abs_forward

app_name = 'history'

urlpatterns = [
    path('activities/', ActivitiesView.as_view(), name='activities-list'),
    path('fees-payments/', FeesPaymentsView.as_view(), name='fees-payments-list'),
    path('bank-statements/', BankStatementsView.as_view(), name='bank-statements-list'),
    path('trades/', TradesView.as_view(), name='trades-list'),
    path('cashflow_weight/', cashflow_weight, name='cashflow-weight'),
    path('performance/', performance, name='performance'),
    path('realized_volatility/', realized_volatility, name='realized-volatility'),
    path('cashflow_abs_forward/', cashflow_abs_forward, name='cashflow-abs-forward'),
    path('account_pnls', account_pnls, name="account-pnls")
]
