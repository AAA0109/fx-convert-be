from django.urls import path, include

from main.apps.slack.api.views import SlackEventsView



urlpatterns = [
    # path('events', SlackEventsView.as_view(), name='slack_events'),
    path('<slug:action>', SlackEventsView.as_view() ) #, name='slack_events'),
]
