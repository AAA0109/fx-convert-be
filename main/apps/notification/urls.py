from django.urls import path
from main.apps.notification import views


app_name = 'notification'
urlpatterns = [
    path('email_preview/', views.EmailPreviewView.as_view(), name='email-preview')
]
