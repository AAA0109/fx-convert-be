from django.urls import path, include
from rest_framework_nested import routers

from main.apps.settlement.api.views.beneficiary import BeneficiaryViewSet
from main.apps.settlement.api.views.wallet import WalletViewSet

app_name = 'settlement'

# /api/beneficiary
beneficiary_router = routers.DefaultRouter()
beneficiary_router.register('beneficiary', BeneficiaryViewSet, basename='beneficiary')
# /api/wallet
wallet_router = routers.DefaultRouter()
wallet_router.register('wallet', WalletViewSet, basename='wallet')
urlpatterns = [
    path('', include(beneficiary_router.urls)),
    path('', include(wallet_router.urls)),
]
