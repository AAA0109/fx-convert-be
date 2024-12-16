from django.urls import path, include
from rest_framework_nested import routers

from main.apps.webhook.api.views.webhook import WebhookViewSet, WebhookEventListView, WebhookEventGroupListView

app_name = 'webhook'

# /api/webhook
router = routers.DefaultRouter()
router.register('', WebhookViewSet, basename='webhook')

urlpatterns = [
    path('events/', WebhookEventListView.as_view(), name='event-list'),
    path('event-groups/', WebhookEventGroupListView.as_view(), name='event-group-list'),
    path('', include(router.urls)),
]
