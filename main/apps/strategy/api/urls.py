from django.urls import path, include
from rest_framework_nested import routers

from main.apps.strategy.api.views.strategy import StrategyViewSet

app_name = 'strategy'

# /api/strategy
router = routers.DefaultRouter()
router.register('', StrategyViewSet, basename='strategy')

urlpatterns = [
    path('', include(router.urls))
]
