from django.core.management.base import BaseCommand

from hi.apps.config.signals import SettingsInitializer
from hi.apps.config.apps import ConfigConfig


class Command(BaseCommand):
    help = 'Sync settings database entries with current code definitions (adds missing entries only)'

    def handle(self, *args, **options):
        self.stdout.write('Syncing settings with current code definitions...')
        
        initializer = SettingsInitializer()
        initializer.run(sender=ConfigConfig)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully synced settings database entries')
        )