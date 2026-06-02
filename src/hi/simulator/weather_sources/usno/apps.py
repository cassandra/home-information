from django.apps import AppConfig


class UsnoWeatherSimConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.weather_sources.usno'

    simulator_module_label = 'US Naval Observatory'

    weather_source_short_name = 'usno'
    weather_source_label = 'US Naval Observatory'
    weather_source_tab_template = 'weather_sources/usno/tab.html'
