from django.urls import path

from main.apps.approval.api.views.approval import (
    ApproveApprovalRequestAPIView,
    ApproverAPIView,
    RequestPaymentApprovalAPIView
)


app_name = 'approval'


urlpatterns = [
    path('approver/', ApproverAPIView.as_view(), name='approval-approver'),
    path('request-payment-approval/', RequestPaymentApprovalAPIView.as_view(),
         name='approval-request-approval'),
    path('approve-request/', ApproveApprovalRequestAPIView.as_view(),
         name='approve-request'),
]
