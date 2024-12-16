from django.urls import path, re_path

from main.apps.auth.views import DecoratedTokenObtainPairView, DecoratedTokenRefreshView, DecoratedTokenVerifyView

app_name = 'auth'

urlpatterns = [
    path('', DecoratedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh', DecoratedTokenRefreshView.as_view(), name='token_refresh'),
    path('verify', DecoratedTokenVerifyView.as_view(), name='token_verify'),
]
