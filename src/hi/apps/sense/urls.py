from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^sensor/history/(?P<sensor_id>\d+)$', 
             views.SensorHistoryView.as_view(), 
             name='sense_sensor_history'),

    re_path( r'^sensor/response/details/(?P<sensor_history_id>\d+)$', 
             views.SensorHistoryDetailsView.as_view(), 
             name='sense_sensor_history_details'),
]
