from django.apps import AppConfig


class HassConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.services.hass'
    simulator_module_label = 'Home Assistant'
