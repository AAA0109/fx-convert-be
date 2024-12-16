from django.urls import path, include
from rest_framework_nested import routers

from main.apps.cashflow.api.views.generator import CashFlowGeneratorViewSet

app_name = 'cashflow'

router = routers.DefaultRouter()
router.register('', CashFlowGeneratorViewSet, basename='cashflow_generator')

urlpatterns = [
    path('', include(router.urls))
]
