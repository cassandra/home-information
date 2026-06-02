from django.apps import AppConfig


class SunriseSunsetWeatherSimConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.weather_sources.sunrise_sunset_org'

    simulator_module_label = 'Sunrise-Sunset.org'

    weather_source_short_name = 'sunrise_sunset_org'
    weather_source_label = 'Sunrise-Sunset.org'
    weather_source_tab_template = 'weather_sources/sunrise_sunset_org/tab.html'
