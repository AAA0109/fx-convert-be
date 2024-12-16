from django.urls import path

from main.apps.ibkr.api.views.eca import CreateIBApplicationView, GetIBAccountStatusesView, \
    GetIBAccountStatusView, CreateECASSOView, GetPendingTasksView, GetRegistrationTasksView
from main.apps.ibkr.api.views.fb import CreateDepositFundsView, GetInstructionNameView, GetStatusView, \
    ListFundingRequestsView, ListWireInstructionsView, CreatePredefinedDestinationInstructionView, \
    CreateWithdrawFundsView
from main.apps.ibkr.api.views.future_contract import FutureContractDetailBySymbolApiView, FutureContractByBaseApiView, \
    FutureContractActiveByBaseApiView, FutureContractActiveListApiView
from main.apps.ibkr.api.views.system import SupportedCompaniesView

app_name = 'ibkr'

urlpatterns = [
    path('ib/eca/application', CreateIBApplicationView.as_view(),
         name='eca-application'),
    path('ib/eca/sso_url', CreateECASSOView.as_view(), name='eca-sso-url'),
    path('ib/eca/account_statuses', GetIBAccountStatusesView.as_view(),
         name='eca-account-statuses'),
    path('ib/eca/account_status', GetIBAccountStatusView().as_view(),
         name='eca-account-status'),
    path('ib/eca/pending_tasks', GetPendingTasksView().as_view(),
         name='eca-pending-tasks'),
    path('ib/eca/registration_tasks', GetRegistrationTasksView().as_view(),
         name='eca-registration-tasks'),

    path('ib/fb/instruction_name', GetInstructionNameView.as_view(),
         name='fb-instruction-name'),
    path('ib/fb/deposit_funds', CreateDepositFundsView.as_view(),
         name='fb-deposit-funds'),
    path('ib/fb/withdraw_fund', CreateWithdrawFundsView.as_view(),
         name='fb-withdraw-funds'),
    path('ib/fb/status', GetStatusView().as_view(), name='fb-status'),
    path('ib/fb/funding_requests', ListFundingRequestsView().as_view(),
         name='fb-funding-requests'),
    path('ib/fb/wire_instructions', ListWireInstructionsView().as_view(),
         name='fb-wire-instruction'),
    path('ib/fb/predefined_destination_instruction',
         CreatePredefinedDestinationInstructionView.as_view(), name='fb-predefined-destination-instruction'),

    path('ib/contract/detail/<str:symbol>',
         FutureContractDetailBySymbolApiView.as_view(), name='future-contract-by-symbol'),
    path('ib/contract/<str:base>', FutureContractByBaseApiView.as_view(),
         name='future-contract-by-base'),
    path('ib/contract/active/<str:base>', FutureContractActiveByBaseApiView.as_view(),
         name='future-contract-active-by-base'),
    path('ib/contract/active/', FutureContractActiveListApiView.as_view(),
         name='future-contract-active'),
    path('ib/system/companies/', SupportedCompaniesView.as_view(),
         name='ib-system-api-supported-companies')
]
