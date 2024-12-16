from django.urls import path, include

from main.apps.ndl.api.views import (
    SGEDetailApiView,
    SGEListApiView,
    PTenAverageView
)


app_name = 'ndl'

urlpatterns = [

    path('sge/list/', SGEListApiView.as_view(), name='SGE-list-view'),
    path('sge/detail/<str:currency_code>/<str:value_type>/',
         SGEDetailApiView.as_view(), name='SGE-detail-view'),
    path('sge/average/p10/<str:value_type>/',
         PTenAverageView.as_view(), name='SGE-p10-average-view'),

]
