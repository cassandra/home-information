from django.urls import path

from . import views


urlpatterns = [
    path( 'api/json',
          views.SunriseSunsetApiView.as_view(),
          name = 'simulator_weather_sunrise_sunset_api' ),

    path( 'state/set',
          views.SunriseSunsetSimStateSetView.as_view(),
          name = 'simulator_weather_sunrise_sunset_state_set' ),
]
