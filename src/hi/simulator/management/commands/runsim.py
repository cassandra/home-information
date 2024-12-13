import os

from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):

    help = "Runs the simulator server (separate port)."

    def add_arguments(self, parser):
        super().add_arguments( parser )
        parser.add_argument(
            '--port', type = int, default = 8001,
            help = 'Port number to run the simulator server on.',
        )
        return

    def handle(self, *args, **options):
        os.environ['DJANGO_SETTINGS_MODULE'] = 'hi.settings.simulator'
        options['addrport'] = str(options['port'])
        super().handle(*args, **options)
        return
    
