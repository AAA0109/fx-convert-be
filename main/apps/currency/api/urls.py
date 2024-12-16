from django.urls import path, include

from rest_framework.routers import DefaultRouter

from main.apps.currency.api.views import (
    CurrencyDeliveryTimeApiView,
    CurrencyListApiView,
    CurrencyDetailApiView,
    DeliveryTimeViewSet,
    FxPairViewSet,
    StabilityIndexListApiView,
    StabilityIndexDetailApiView
)

app_name = 'currency'

router = DefaultRouter()
router.register(r'fxpairs', FxPairViewSet, basename='fxpair')
router.register(r'delivery-time', DeliveryTimeViewSet, basename='delivery-time')

urlpatterns = [
    path('currencies/', CurrencyListApiView.as_view(), name='currency-list'),
    path('currencies/<str:mnemonic>/', CurrencyDetailApiView.as_view(), name='currency-detail'),
    path('stability-indexes/', StabilityIndexListApiView.as_view(), name='stability-indexes-list'),
    path('stability-index/<str:mnemonic>/<str:year>', StabilityIndexDetailApiView.as_view(), name='stability-indexes-detail'),
    path('', include(router.urls)),
    path('currency-deliverytime/<str:mnemonic>/', CurrencyDeliveryTimeApiView.as_view(), name='delivery-time-by-menmonic')
]
