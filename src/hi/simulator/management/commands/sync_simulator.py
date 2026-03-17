from django.core.management.base import BaseCommand

from hi.simulator.apps import SimulatorConfig
from hi.simulator.initializers import SimulatorInitializer


class Command(BaseCommand):
    help = 'Sync simulator database entries with current code definitions (adds missing entries only)'

    def handle(self, *args, **options):
        self.stdout.write('Syncing simulator with current code definitions...')

        initializer = SimulatorInitializer()
        initializer.run( sender = SimulatorConfig )

        self.stdout.write(
            self.style.SUCCESS('Successfully synced simulator database entries')
        )
