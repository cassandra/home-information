import json
from django.core.management.base import BaseCommand, CommandError
from hi.tests.dev_injection import DevInjectionManager


class Command(BaseCommand):
    help = 'Inject test data into API responses for frontend development testing'

    def add_arguments(self, parser):
        parser.add_argument(
            'injection_type', 
            choices=['transient_view'],
            help='Type of data to inject'
        )
        parser.add_argument(
            'data', 
            help='JSON data to inject'
        )
        parser.add_argument(
            '--persistent', 
            action='store_true',
            help='Use persistent injection instead of one-time (default: one-time)'
        )
        parser.add_argument(
            '--cache', 
            action='store_true',
            help='Use cache storage instead of file storage (default: file)'
        )
        parser.add_argument(
            '--clear', 
            action='store_true',
            help='Clear all existing overrides instead of injecting'
        )
        parser.add_argument(
            '--list', 
            action='store_true',
            help='List all active overrides'
        )

    def handle(self, *args, **options):
        # Handle special actions first
        if options['list']:
            active = DevInjectionManager.list_active_overrides()
            if active:
                self.stdout.write(self.style.SUCCESS("Active overrides:"))
                for key, value in active.items():
                    self.stdout.write(f"  {key}: {value}")
            else:
                self.stdout.write("No active overrides")
            return

        if options['clear']:
            success = DevInjectionManager.clear_all_overrides()
            if success:
                self.stdout.write(self.style.SUCCESS("Cleared all overrides"))
            else:
                self.stdout.write(self.style.ERROR("Failed to clear overrides (not in DEBUG mode?)"))
            return

        # Parse and validate JSON data
        try:
            data = json.loads(options['data'])
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON data: {e}")

        # Inject based on type
        injection_type = options['injection_type']
        one_time = not options['persistent']
        use_cache = options['cache']

        if injection_type == 'transient_view':
            # Validate transient view data structure
            required_keys = ['url']
            optional_keys = ['durationSeconds', 'priority', 'triggerReason']
            
            for key in required_keys:
                if key not in data:
                    raise CommandError(f"Missing required key '{key}' in transient view data")
            
            success = DevInjectionManager.inject_transient_view(
                data, one_time=one_time, use_cache=use_cache
            )
        else:
            raise CommandError(f"Unknown injection type: {injection_type}")

        if success:
            storage_type = "cache" if use_cache else "file"
            persistence = "one-time" if one_time else "persistent"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Injected {injection_type} data ({persistence}, {storage_type})"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Injection failed - check that DEBUG mode is enabled and "
                    "DEBUG_FORCE_TRANSIENT_VIEW_OVERRIDE is True in settings"
                )
            )