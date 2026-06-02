from django.urls import path

from . import views


urlpatterns = [
    path( 'api/oneday',
          views.UsnoApiView.as_view(),
          name = 'simulator_weather_usno_api' ),

    path( 'state/set',
          views.UsnoSimStateSetView.as_view(),
          name = 'simulator_weather_usno_state_set' ),
]
