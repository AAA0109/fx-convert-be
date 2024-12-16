from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from main.settings.base import API_SCOPE

urlpatterns = [
    path(r'schema/', SpectacularAPIView.as_view(api_version='v2'), name='v2schema'),
    path(r'schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='v2schema'), name='swagger-ui2'),
    path(r'schema/redoc/', SpectacularRedocView.as_view(url_name='v2schema'), name='redoc'),
]

if API_SCOPE == 'internal':
    urlpatterns += [
        path('history/', include('main.apps.history.api.v2.urls')),
    ]
