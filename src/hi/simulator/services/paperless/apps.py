from django.apps import AppConfig


class PaperlessConfig( AppConfig ):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hi.simulator.services.paperless'
    simulator_module_label = 'Paperless-ngx'
