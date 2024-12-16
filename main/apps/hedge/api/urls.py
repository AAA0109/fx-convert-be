from django.urls import path, include
from rest_framework import routers

from main.apps.hedge.api.views.fx_forward import DraftFxForwardViewSet
from main.apps.hedge.api.views.hedging import *
from main.apps.hedge.api.views.update_ndf import UpdateNDFViewSet
from main.apps.hedge.api.views.update_request import UpdateRequestViewSet

router = routers.DefaultRouter()
router.register(r'', HedgingViewSet)
router.register(r'forward/update/request', UpdateRequestViewSet, basename='update-request')
router.register(r'forward/ndf', UpdateNDFViewSet, basename='forward-ndf')
router.register(r'forward', DraftFxForwardViewSet)
app_name = 'hedging'

urlpatterns = [
    path('', include(router.urls)),
]
