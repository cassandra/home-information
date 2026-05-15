from django.urls import path

from . import views


urlpatterns = [

    path( 'sensor/response/details/<int:sensor_history_id>',
          views.SensorHistoryDetailsView.as_view(),
          name='sense_sensor_history_details'),
]
