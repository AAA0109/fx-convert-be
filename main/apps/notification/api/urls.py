from django.urls import path, include
from rest_framework import routers
from main.apps.notification.api.views.notification import NotificationEventViewSet, UserNotificationViewSet, \
    ResendNotificationView

notification_router = routers.DefaultRouter()
notification_router.register(r'events', NotificationEventViewSet)
notification_router.register(r'user', UserNotificationViewSet)

app_name = 'notification'
urlpatterns = [
    path('', include(notification_router.urls)),
    path('resend', ResendNotificationView.as_view(), name='notification-resend')
]
