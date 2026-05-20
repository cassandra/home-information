from django.apps import AppConfig


class NwsWeatherSimConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.weather_sources.nws'

    simulator_module_label = 'National Weather Service'

    weather_source_short_name = 'nws'
    weather_source_label = 'National Weather Service'
    weather_source_tab_template = 'weather_sources/nws/tab.html'
