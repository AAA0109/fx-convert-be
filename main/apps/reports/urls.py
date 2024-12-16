from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path

from main.apps.reports.views import CurrencyMovementReportView

app_name = 'reports'

urlpatterns = [
    path('currency-movement', staff_member_required(CurrencyMovementReportView.as_view())),
]
