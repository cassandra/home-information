from django.urls import path

from . import views


urlpatterns = [
    path( 'api/alerts/active',
          views.NwsAlertsActiveView.as_view(),
          name = 'simulator_weather_nws_alerts_active' ),

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
