from django.core.management.base import BaseCommand

from hi.integrations.apps import IntegrationsConfig
from hi.integrations.initializers import IntegrationInitializer


class Command(BaseCommand):
    help = 'Sync integration database entries with current code definitions (adds missing entries only)'

    def handle(self, *args, **options):
        self.stdout.write('Syncing integrations with current code definitions...')

        initializer = IntegrationInitializer()
        initializer.run( sender = IntegrationsConfig )

        self.stdout.write(
            self.style.SUCCESS('Successfully synced integration database entries')
        )
