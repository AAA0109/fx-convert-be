from django.urls import path, include
from rest_framework_nested import routers

from main.apps.account.api.views.account import AccountViewSet
from main.apps.account.api.views.autopilot_data import AutopilotDataViewSet
from main.apps.account.api.views.cashflow import CashflowViewSet, CashflowNoteViewSet
from main.apps.account.api.views.cashflows import CashflowsViewSet
from main.apps.account.api.views.company import CompanyViewSet, CompanyContactOrderViewSet, CompanyUserViewSet, \
    GetCompanyByEINView, CompanySupportedCurrencyViewSet, CompanyJoinRequestViewSet, CreateCompanyJoinRequestView, \
    ApproveCompanyJoinRequestView, RejectCompanyJoinRequestView
from main.apps.account.api.views.draft import DraftCashflowsViewSet
from main.apps.core.views import gmail_authenticate
from main.apps.account.api.views.installment_cashflow import InstallmentViewSet
from main.apps.account.api.views.invite import ExtendInviteUserView, ExtendSetUserPasswordView, InviteUserTokenView
from main.apps.account.api.views.parachute_data import ParachuteDataViewSet
from main.apps.account.api.views.password import ChangePasswordView
from main.apps.account.api.views.support import SendAuthenticatedSupportMessageView, SendGeneralSupportMessageView
from main.apps.account.api.views.user import UserViewSet, ActivateUserView, UserEmailExistsView, UserConfirmPhoneView, \
    UserVerifyPhoneOTPView, UpdateUserPermissionGroupView, RemoveUserCompanyView

app_name = 'account'

# /api/accounts/
router = routers.DefaultRouter()
router.register(r'accounts', AccountViewSet)

# /api/accounts/<account_id>/cashflow
cashflow_router = routers.NestedSimpleRouter(router, r'accounts', lookup='account')
cashflow_router.register('cashflow', CashflowViewSet)

# /api/accounts/<account_id>/cashflow/{cashflow_pk}/notes
cashflow_note_router = routers.NestedSimpleRouter(cashflow_router, r'cashflow', lookup='cashflow')
cashflow_note_router.register('notes', CashflowNoteViewSet, basename='notes')

# /api/account/<account_id>/parachute_data
parachute_data_router = routers.NestedSimpleRouter(router, r'accounts', lookup='account')
parachute_data_router.register('parachute_data', ParachuteDataViewSet, basename="account-parachute-data")

# /api/account/<account_id>/autopilot_data
autopilot_data_router = routers.NestedSimpleRouter(router, r'accounts', lookup='account')
autopilot_data_router.register('autopilot_data', AutopilotDataViewSet, basename="account-autopilot-data")

# /api/installments
router.register('installments', InstallmentViewSet, basename='installments')

# /api/company
router.register(r'company', CompanyViewSet)

# /api/company/<company_id>/users
company_user_router = routers.NestedSimpleRouter(router, r'company', lookup='company')
company_user_router.register('user', CompanyUserViewSet)

# /api/company/<company_id>/currencies
company_currencies_router = routers.NestedSimpleRouter(router, r'company', lookup='company')
company_currencies_router.register('currencies', CompanySupportedCurrencyViewSet)

# /api/company/<company_id>/contact_order
contact_order_router = routers.NestedSimpleRouter(router, r'company', lookup='company')
contact_order_router.register('contact_order', CompanyContactOrderViewSet)

# /api/company/<company_id>/join_request
join_request_router = routers.NestedSimpleRouter(router, r'company', lookup='company')
join_request_router.register('join_request', CompanyJoinRequestViewSet)

# /api/user
router.register(r'user', UserViewSet)

# /api/cashflows
router.register(r'cashflows', CashflowsViewSet, basename='cashflows')

# /api/drafts
router.register(r'drafts', DraftCashflowsViewSet, basename='drafts')

# /api/accounts/<account_id>/cashflow/<cashflow_id>/draft
cashflow_draft_router = routers.NestedSimpleRouter(cashflow_router, r'cashflow', lookup='cashflow')
cashflow_draft_router.register('draft', CashflowViewSet.Draft, basename='draft')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(parachute_data_router.urls)),
    path('', include(autopilot_data_router.urls)),
    path('', include(cashflow_router.urls)),
    path('', include(cashflow_note_router.urls)),
    path('', include(cashflow_draft_router.urls)),
    path('', include(company_user_router.urls)),
    path('', include(company_currencies_router.urls)),
    path('', include(contact_order_router.urls)),
    path('', include(join_request_router.urls)),
    path('invite/', ExtendInviteUserView.as_view(), name='invite-user'),
    path('invite/confirm', ExtendSetUserPasswordView.as_view(), name='confirm-user'),
    path('invite/verify-token', InviteUserTokenView.as_view(), name='invite-verify-token'),
    path('user/activate', ActivateUserView.as_view(), name='activate-user'),
    path('user/exists', UserEmailExistsView.as_view(), name='user-exists'),
    path('user/phone/confirm', UserConfirmPhoneView.as_view(), name='user-confirm-phone'),
    path('user/phone/verify-otp', UserVerifyPhoneOTPView.as_view(), name='user-verify-phone-otp'),
    path('user/<int:id>/permission', UpdateUserPermissionGroupView.as_view(), name='user-permission-update'),
    path('user/<int:id>/remove', RemoveUserCompanyView.as_view(), name='user-remove-company'),
    path('password/change-password', ChangePasswordView.as_view(), name='change-password'),
    path('password/password-reset/', include('django_rest_passwordreset.urls')),
    path('support/message', SendAuthenticatedSupportMessageView.as_view(), name='support-message'),
    path('support/general/message', SendGeneralSupportMessageView.as_view(), name='support-general-message'),
    path('company/ein', GetCompanyByEINView.as_view(), name='company-ein'),
    path('company/<int:company_pk>/join_request', CreateCompanyJoinRequestView.as_view(),
         name='company-join-requests'),
    path('company/<int:company_pk>/join_request/<int:id>/approve', ApproveCompanyJoinRequestView.as_view(),
         name='company-join-request-approve'),
    path('company/<int:company_pk>/join_request/<int:id>/reject', RejectCompanyJoinRequestView.as_view(),
         name='company-join-request-reject'),
    path('gmail/authenticate', gmail_authenticate, name='gmail-authenticate')
    # TODO: remove after proper implementation
]
