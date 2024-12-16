from django.urls import path
from main.apps.payment.api.views.market_spot_date import MarketSpotDateAPIView
from main.apps.payment.api.views.payment_rfq import PaymentExecutionAPIView, PaymentRfqAPIView
from main.apps.payment.api.views.bulk_payment_rfq import BulkPaymentRfqAPIView
from main.apps.payment.api.views.bulk_payment_execute import BulkPaymentExecutionAPIView

from main.apps.payment.api.views.payment import (
    PaymentViewSet,
    PaymentCashflowViewSet
)
from main.apps.payment.api.views.bulk_payment import BulkPaymentViewSet, BulkPaymentValidationViewSet
from main.apps.payment.api.views.stripe.payment_method import StripePaymentMethodView
from main.apps.payment.api.views.stripe.setup_intent import StripeSetupIntentView
from main.apps.payment.api.views.calendar import ValueDateCalendarAPIView

app_name = 'payment'


urlpatterns = [
    path('stripe/setup_intent', StripeSetupIntentView.as_view(), name='stripe-setup-intent'),
    path('stripe/payment_method', StripePaymentMethodView.as_view(), name='stripe-payment-method'),
    path('',
         PaymentViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='payment-cashflow'
    ),
    path('<int:pk>/',
         PaymentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
         name='payment-cashflow-with-pk'
    ),
    path('calendar/value-date/', ValueDateCalendarAPIView.as_view(), name='value-date-calendar'),
    path('<int:payment_id>/cashflows/',
         PaymentCashflowViewSet.as_view({'get': 'list', 'post': 'create'}),
         name='payment-cashflows'
    ),
    path('<int:payment_id>/cashflows/<str:cashflow_id>/',
         PaymentCashflowViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
         name='payment-cashflows-with-pk'
    ),
    path('<int:pk>/rfq/', PaymentRfqAPIView.as_view(), name='payment-rfq'),
    path('<int:pk>/execute/', PaymentExecutionAPIView.as_view(), name='payment-execution'),
    path('bulk-payments/',
         BulkPaymentViewSet.as_view({'post': 'create', 'put': 'update'}),
         name='bulk-payment-cashflow'
    ),
    path('bulk-payments/validate/',
         BulkPaymentValidationViewSet.as_view({'post': 'create'}),
         name='bulk-payment-validate'
    ),
    path('bulk-payments-rfq/', BulkPaymentRfqAPIView.as_view(), name='bulk-payment-rfq'),
    path('bulk-payments-execution/', BulkPaymentExecutionAPIView.as_view(), name='bulk-payment-execution'),
    path('market-spot-dates/', MarketSpotDateAPIView.as_view(), name='market-spot-dates'),
]
