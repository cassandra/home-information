from django.urls import path

from . import views


urlpatterns = [
    path( 'api/v1/forecast',
          views.OpenMeteoForecastApiView.as_view(),
          name = 'simulator_weather_openmeteo_forecast' ),

    path( 'api/archive',
          views.OpenMeteoArchiveApiView.as_view(),
          name = 'simulator_weather_openmeteo_archive' ),

    path( 'state/set',
          views.OpenMeteoSimStateSetView.as_view(),
          name = 'simulator_weather_openmeteo_state_set' ),
]
