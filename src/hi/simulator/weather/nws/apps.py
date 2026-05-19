from django.apps import AppConfig


class NwsWeatherSimConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.weather.nws'

    weather_source_short_name = 'nws'
    weather_source_label = 'National Weather Service'
    weather_source_tab_template = 'simulator/weather/nws/tab.html'
