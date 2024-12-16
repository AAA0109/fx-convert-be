from django.urls import path

from main.apps.corpay.views import ForwardView, ForwardCreateView

app_name = 'corpay'

urlpatterns = [
    path('forward_edit/<int:pk>', ForwardView.as_view(), name='forward_edit'),
    path('forward_create/<int:updaterequest_id>', ForwardCreateView.as_view(), name='forward_create'),
]
