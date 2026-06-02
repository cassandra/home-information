from django.apps import AppConfig


class OpenMeteoWeatherSimConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.weather_sources.openmeteo'

    simulator_module_label = 'Open-Meteo'

    weather_source_short_name = 'openmeteo'
    weather_source_label = 'Open-Meteo'
    weather_source_tab_template = 'weather_sources/openmeteo/tab.html'
