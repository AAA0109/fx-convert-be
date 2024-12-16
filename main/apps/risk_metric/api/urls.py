from django.urls import path, include

from rest_framework.routers import DefaultRouter

from main.apps.risk_metric.api.views import (
    CashFlowRiskApiView,
    get_cashflow_risk_cones_view, get_margin_and_fee_view, get_margin_health_report
)
app_name = 'risk_metric'
urlpatterns = [
    path('get_cashflow_risk_cones/', get_cashflow_risk_cones_view, name='cashflow-risk-cones'),
    path('margin_and_fees/', get_margin_and_fee_view, name='margin-fee'),
    path('margin_health/', get_margin_health_report, name='margin-health'),
]
