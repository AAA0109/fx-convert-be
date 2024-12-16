"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import re_path, path, include

from main.apps.core.views import index
from main.settings.base import API_SCOPE
from main.urls.api.base import urlpatterns as api_base_urlpatterns
from main.urls.api.legacy import urlpatterns as api_legacy_urlpatterns
from main.urls.api.v1 import urlpatterns as api_v1_urlpatterns
from main.urls.api.v2 import urlpatterns as api_v2_urlpatterns

app_name = 'main'
urlpatterns = [
    path('', index, name='index'),
    # TODO: Backwards compatibility support, deprecate this once FE move to using /api/v[0-9]+ pattern
    path('api/',
         include((api_base_urlpatterns + api_legacy_urlpatterns + api_v1_urlpatterns, app_name), namespace='')),
    path('api/v1/', include((api_base_urlpatterns + api_v1_urlpatterns, app_name), namespace='v1')),
    path('api/v2/', include((api_base_urlpatterns + api_v2_urlpatterns, app_name), namespace='v2')),
]
if API_SCOPE == 'internal':
    urlpatterns += [
        path('admin/', include('massadmin.urls')),
        re_path(r'^admin/', admin.site.urls),
        re_path(r'^accounts/', include('django.contrib.auth.urls')),
        path('views/corpay/', include('main.apps.corpay.urls')),
        path('views/core/', include('main.apps.core.urls')),
        path('notification/', include('main.apps.notification.urls')),
        path('reports/', include('main.apps.reports.urls')),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG and settings.APP_ENVIRONMENT == 'local':
    urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
