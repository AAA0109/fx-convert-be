from django.urls import path

from main.apps.dataprovider.api.views.profile import RetrieveProfileParallelOptionView

app_name = 'dataprovider'


urlpatterns = [
    path('profile/parallel-option', RetrieveProfileParallelOptionView.as_view(),
         name="retrieve-profile-parallel-option"),
]
