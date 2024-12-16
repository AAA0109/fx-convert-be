from django.urls import path, include
from rest_framework.routers import DefaultRouter
from main.apps.oems.api.views.liquidity import LiquidityInsightApiView

from main.apps.oems.api.views.settlement import NonSettlementDaysView, SettlementDaysView, IsValidSettlementDayView, \
    NextValidSettlementDayView, PrevValidSettlementDayView, NextMktDayView, CurrentMktDayView, FxSettlementInfoView, \
     FxSpotValueDateView, BestExecutionView, ValueDateValidator
from main.apps.oems.api.views.ticket import TicketViewSet
from main.apps.oems.views import CnyExecutionView
from main.apps.oems.api.views.best_execution import BestExecutionTimingAPIView

# =======

from main.apps.oems.api.views.rfq import RfqViewSet
from main.apps.oems.api.views.execute_rfq import ExecuteRfqViewSet
from main.apps.oems.api.views.execute import ExecuteViewSet, BatchAllorNoneExecute
from main.apps.oems.api.views.fund import FundTransactionViewSet
from main.apps.oems.api.views.status import StatusViewSet
from main.apps.oems.api.views.external_ticket import ExternalTicketViewSet, ExternalMtmViewSet
from main.apps.oems.api.views.req_activate import ReqExecuteActivate
from main.apps.oems.api.views.req_authorize import ReqExecuteAuthorize
from main.apps.oems.api.views.req_cancel import ReqExecuteCancel
from main.apps.oems.api.views.req_pause import ReqExecutePause
from main.apps.oems.api.views.req_resume import ReqExecuteResume
from main.apps.oems.api.views.manual_request import ManualRequestViewSet

# =======

from main.apps.oems.api.views.quote import QuoteViewSet, QuoteToTicketAPIView
from main.apps.oems.api.views.wait_condition import WaitConditionViewSet
from main.settings.base import API_SCOPE

app_name = 'oems'

router = DefaultRouter()

router.register('execute', ExecuteViewSet, basename="oems-execute")
router.register('rfq', RfqViewSet, basename="oems-rfq")
router.register('execute-rfq', ExecuteRfqViewSet, basename="oems-execute-rfq")
router.register('fund', FundTransactionViewSet, basename="oems-fund")
router.register('status', StatusViewSet, basename="oems-status")
router.register('execution', ExternalTicketViewSet, basename="oems-execution")
router.register('mtm', ExternalMtmViewSet, basename="oems-mtm")

router.register('execute/activate', ReqExecuteActivate, basename="oems-execute-activate")
router.register('execute/authorize', ReqExecuteAuthorize, basename="oems-execute-authorize")
router.register('execute/cancel', ReqExecuteCancel, basename="oems-execute-cancel")
router.register('execute/pause', ReqExecutePause, basename="oems-execute-pause")
router.register('execute/resume', ReqExecuteResume, basename="oems-execute-resume")

from django.shortcuts import resolve_url

if API_SCOPE == 'internal':
    router.register('batch', BatchAllorNoneExecute, basename="oems-batch")
    router.register('cny-execution', CnyExecutionView, basename="oems-cny-execution")
    router.register('ticket', TicketViewSet, basename="oems-ticket")

# TODO: Ikhwan to clean this up
quote_create = QuoteViewSet.as_view({
    'post': 'create'
})

wait_condition_create = WaitConditionViewSet.as_view({
    'post': 'create'
})

slack_form = ManualRequestViewSet.as_view({
    'post': 'create',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path('', include(router.urls)),
    path('execute/best-execution', BestExecutionView.as_view(), name='best-execution'),
]

if API_SCOPE == 'internal':
    urlpatterns += [
        path('order-quote/', quote_create, name='create-quote'),
        path('quote-to-ticket/', QuoteToTicketAPIView.as_view(), name='quote-to-ticket'),
        path('wait-condition/', wait_condition_create, name='create-wait-condition'),
        path('manual-request-slack-form/', slack_form, name='slack-form'),
        path('calendar/non-settlement-days', NonSettlementDaysView.as_view(), name='non-settlement-days'),
        path('calendar/settlement-days', SettlementDaysView.as_view(), name='settlement-days'),
        path('calendar/valid-settlement-day', IsValidSettlementDayView.as_view(), name='valid-settlement-day'),
        path('calendar/next-valid-settlement-day', NextValidSettlementDayView.as_view(),
             name='next-valid-settlement-day'),
        path('calendar/prev-valid-settlement-day', PrevValidSettlementDayView.as_view(),
             name='prev-valid-settlement-day'),
        path('calendar/next-mkt-day', NextMktDayView.as_view(), name='next-mkt-day'),
        path('calendar/current-mkt-day', CurrentMktDayView.as_view(), name='current-mkt-day'),
        path('calendar/fx-settlement-info', FxSettlementInfoView.as_view(), name='fx-settlement-info'),
        path('calendar/spot-value-date', FxSpotValueDateView.as_view(), name='spot-value-date'),
        path('calendar/value-dates', ValueDateValidator.as_view(), name='value-dates'),
        path('best-execution-timing/<int:payment_id>/', BestExecutionTimingAPIView.as_view(), name="best-execution-timings"),
        path('liquidity-insight/', LiquidityInsightApiView.as_view(), name="liquidity-insight"),
    ]
