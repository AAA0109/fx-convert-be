from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from main.settings.base import API_SCOPE

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(api_version='v1'), name='v1schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='v1schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='v1schema'), name='redoc')
]

if API_SCOPE == 'internal':
    urlpatterns += [
        path('history/', include('main.apps.history.api.v1.urls')),
    ]
