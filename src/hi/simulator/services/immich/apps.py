from django.apps import AppConfig


class ImmichConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.services.immich'
    simulator_module_label = 'Immich'
