from django.urls import path
from main.apps.auth.api.views.trench.base import (
    ExtendMFAConfigView,
    ExtendMFAListActiveUserMethodsView,
    ExtendMFAMethodActivationView,
    ExtendMFAMethodBackupCodesRegenerationView,
    ExtendMFAMethodConfirmActivationView,
    ExtendMFAMethodDeactivationView,
    ExtendMFAMethodRequestCodeView,
    ExtendMFAPrimaryMethodChangeView
)
from main.apps.auth.api.views.trench.jwt import (
    ExtendMFAFirstStepJWTView,
    ExtendMFASecondStepJWTView
)

app_name = 'auth_api'

urlpatterns = [
    path(
        "<str:method>/activate/",
        ExtendMFAMethodActivationView.as_view(),
        name="mfa-activate",
    ),
    path(
        "<str:method>/activate/confirm/",
        ExtendMFAMethodConfirmActivationView.as_view(),
        name="mfa-activate-confirm",
    ),
    path(
        "<str:method>/deactivate/",
        ExtendMFAMethodDeactivationView.as_view(),
        name="mfa-deactivate",
    ),
    path(
        "<str:method>/codes/regenerate/",
        ExtendMFAMethodBackupCodesRegenerationView.as_view(),
        name="mfa-regenerate-codes",
    ),
    path("code/request/", ExtendMFAMethodRequestCodeView.as_view(), name="mfa-request-code"),
    path("mfa/config/", ExtendMFAConfigView.as_view(), name="mfa-config-info"),
    path(
        "mfa/user-active-methods/",
        ExtendMFAListActiveUserMethodsView.as_view(),
        name="mfa-list-user-active-methods",
    ),
    path(
        "mfa/change-primary-method/",
        ExtendMFAPrimaryMethodChangeView.as_view(),
        name="mfa-change-primary-method",
    ),
    path("login/", ExtendMFAFirstStepJWTView.as_view(), name="generate-code-jwt"),
    path("login/code/", ExtendMFASecondStepJWTView.as_view(), name="generate-token-jwt"),
]
