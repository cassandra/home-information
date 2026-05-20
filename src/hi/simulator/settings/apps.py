from django.apps import AppConfig


class SettingsConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.settings'
    label = 'simulator_settings'
