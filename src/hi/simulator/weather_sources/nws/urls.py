from django.urls import path

from . import views


urlpatterns = [
    path( 'api/alerts/active',
          views.NwsAlertsActiveView.as_view(),
          name = 'simulator_weather_nws_alerts_active' ),

    # Current-conditions / forecast chain (points → stations →
    # observations + forecasts). The main app follows the URLs our
    # points/stations responses hand back.
    path( 'api/points/<str:coords>',
          views.NwsPointsView.as_view(),
          name = 'simulator_weather_nws_points' ),

    path( 'api/gridpoints/<str:office>/<str:grid>/stations',
          views.NwsStationsView.as_view(),
          name = 'simulator_weather_nws_stations' ),

    path( 'api/gridpoints/<str:office>/<str:grid>/forecast/hourly',
          views.NwsForecastHourlyView.as_view(),
          name = 'simulator_weather_nws_forecast_hourly' ),

    path( 'api/gridpoints/<str:office>/<str:grid>/forecast',
          views.NwsForecastView.as_view(),
          name = 'simulator_weather_nws_forecast' ),

    path( 'api/stations/<str:station_id>/observations/latest',
          views.NwsObservationsView.as_view(),
          name = 'simulator_weather_nws_observations' ),

    path( 'conditions/set',
          views.NwsSimConditionsSetView.as_view(),
          name = 'simulator_weather_nws_conditions_set' ),

    path( 'alert/add',
          views.NwsSimAlertAddView.as_view(),
          name = 'simulator_weather_nws_alert_add' ),

    path( 'alert/<int:alert_id>/edit',
          views.NwsSimAlertEditView.as_view(),
          name = 'simulator_weather_nws_alert_edit' ),

    path( 'alert/<int:alert_id>/delete',
          views.NwsSimAlertDeleteView.as_view(),
          name = 'simulator_weather_nws_alert_delete' ),

    path( 'alert/<int:alert_id>/toggle',
          views.NwsSimAlertToggleView.as_view(),
          name = 'simulator_weather_nws_alert_toggle' ),
]
