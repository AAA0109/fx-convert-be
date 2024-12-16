from django.urls import path, include

from main.apps.marketing.api.views import (
    FetchCurrencyRateApiView,
    SendMappedDemoForm,
)

app_name = 'marketing'

urlpatterns = [
    path('fx/calculator/rate',  FetchCurrencyRateApiView.as_view(),  name="fx-currency-calculator",),
    path('demo-form/submit', SendMappedDemoForm.as_view(), name="demo-form-submit",),
]
