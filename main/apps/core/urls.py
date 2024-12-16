from django.urls import path

from main.apps.core.views import OauthConnectListView

app_name = 'core'

urlpatterns = [
    path('connect-oauth/', OauthConnectListView.as_view(), name='connect-oauth'),
]
