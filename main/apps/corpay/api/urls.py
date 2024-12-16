from django.urls import path, include

from main.apps.corpay.api.views.beneficiary import RetrieveBeneficiaryRulesView, BeneficiaryView, ListBeneficiaryView, \
    ListBankView, CreateIBANValidationView
from main.apps.corpay.api.views.cost import RetrieveCostView
from main.apps.corpay.api.views.currency_definition import CurrencyDefinitionViewSet
from main.apps.corpay.api.views.forwards import CreateForwardQuoteView, CreateForwardBookQuoteView, \
    CreateForwardCompleteOrderView
from main.apps.corpay.api.views.mass_payment import CorPayQuotePaymentsView, CorPayBookPaymentsView

from main.apps.corpay.api.views.onboarding import CreateClientOnboardingView, RetrieveOnboardingPickListView, \
    CreateClientOnboardingFileUploadView
from main.apps.corpay.api.views.payment import CorPayQuotePaymentView, CorPayBookPaymentView
from main.apps.corpay.api.views.proxy import CorPayProxyView
from main.apps.corpay.api.views.settlement_accounts import ListSettlementAccountsView, ListFXBalanceAccountsView, \
    ListFXBalanceHistoryView, ListCompanyFXBalanceHistoryView
from main.apps.corpay.api.views.spot import CreateSpotRateView, CreateBookSpotDealView, CreateInstructSpotDealView, \
    ListPurposeOfPaymentView, CreateBookAndInstructSpotDealView, SaveInstructDealRequestView
from main.apps.corpay.api.views.fxpairs import SupportedPairViewset
from rest_framework import routers
from main.apps.corpay.api.views.credit import CreditUtilizationViewset

app_name = 'corpay'

corpay = routers.DefaultRouter()
corpay.register(r'fxpairs', SupportedPairViewset, basename='fxpairs')
corpay.register('credit-utilization', CreditUtilizationViewset, basename='credit-utilization')
corpay.register('currency-definition', CurrencyDefinitionViewSet, basename='currency-definition')

urlpatterns = [
    path('corpay/spot/rate', CreateSpotRateView.as_view(), name="create-spot-rate"),
    path('corpay/spot/book-deal', CreateBookSpotDealView.as_view(), name="create-book-spot-deal"),
    path('corpay/spot/instruct-deal', CreateInstructSpotDealView.as_view(), name="create-instruct-spot-deal"),
    path('corpay/spot/book-instruct-deal', CreateBookAndInstructSpotDealView.as_view(),
         name="create-book-instruct-spot-deal"),
    path('corpay/spot/purpose-of-payment', ListPurposeOfPaymentView.as_view(), name="list-purpose-of-payment"),
    path('corpay/settlement/accounts', ListSettlementAccountsView.as_view(), name="list-settlement-accounts"),
    path('corpay/fx-balance/accounts', ListFXBalanceAccountsView.as_view(), name="list-fx-balance-accounts"),
    path('corpay/fx-balance/history', ListFXBalanceHistoryView.as_view(), name="list-fx-balance-histories"),
    path('corpay/fx-balance/company', ListCompanyFXBalanceHistoryView.as_view(),
         name='list-company-fx-balance-histories'),
    path('corpay/beneficiary/banks', ListBankView.as_view(), name="list-banks"),
    path('corpay/beneficiary/iban-validation', CreateIBANValidationView.as_view(), name="create-iban-validation"),
    path('corpay/beneficiary/rules', RetrieveBeneficiaryRulesView.as_view(), name='retrieve-beneficiary-rules'),
    path('corpay/beneficiary', BeneficiaryView.as_view(), name='create-beneficiary'),
    path('corpay/beneficiaries', ListBeneficiaryView.as_view(), name='list-beneficiaries'),
    path('corpay/client-onboarding', CreateClientOnboardingView.as_view(), name="create-client-onboarding"),
    path('corpay/client-onboarding/picklist', RetrieveOnboardingPickListView.as_view(),
         name="retrieve-client-onboarding-picklist"),
    path('corpay/client-onboarding/upload', CreateClientOnboardingFileUploadView.as_view(),
         name='create-client-onboarding-file-upload'),
    path('corpay/costs', RetrieveCostView.as_view(), name='retrieve-cost'),
    path('corpay/proxy', CorPayProxyView.as_view(), name='create-proxy'),
    path('corpay/', include(corpay.urls)),
    path('corpay/spot/save-instruct-deal-request', SaveInstructDealRequestView.as_view(),
         name="save-instruct-deal-request"),
    path('corpay/forward/quote', CreateForwardQuoteView.as_view(), name="create-forward-quote"),
    path('corpay/forward/book-quote', CreateForwardBookQuoteView.as_view(), name="create-forward-book-quote"),
    path('corpay/forward/complete-order', CreateForwardCompleteOrderView.as_view(),
         name="create-forward-complete-order"),
    path('corpay/mass-payments/quote-payments', CorPayQuotePaymentsView.as_view(),
         name='create-quote-payments'),
    path('corpay/mass-payments/book-payments', CorPayBookPaymentsView.as_view(),
         name='create-book-payments'),
    path('corpay/payment/quote', CorPayQuotePaymentView.as_view(), name="create-quote-payment"),
    path('corpay/payment/book', CorPayBookPaymentView.as_view(),
         name='create-book-payment')
]
