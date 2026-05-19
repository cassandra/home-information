from django.urls import path

from . import views


urlpatterns = [
    path( '',
          views.SettingsView.as_view(),
          name = 'simulator_settings' ),

    path( 'runtime/temperature-unit-override',
          views.TemperatureUnitOverrideSetView.as_view(),
          name = 'simulator_temperature_unit_override_set' ),
]
