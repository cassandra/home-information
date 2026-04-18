from django.core.management.base import BaseCommand

from hi.apps.entity.models import EntityAttribute
from hi.apps.location.models import LocationAttribute
from hi.apps.attribute.enums import AttributeValueType
from hi.apps.attribute.thumbnail import AttributeThumbnail


class Command(BaseCommand):
    help = 'Backfill missing thumbnails for existing file attributes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without writing files.',
        )

    def handle(self, *args, **options):
        dry_run = bool(options['dry_run'])

        scanned = 0
        supported = 0
        unsupported = 0
        skipped_existing = 0
        generated = 0
        failed = 0
        would_generate = 0

        model_classes = [EntityAttribute, LocationAttribute]
        self.stdout.write('Processing models: EntityAttribute, LocationAttribute')

        for model_class in model_classes:
            queryset = model_class.objects.filter(
                value_type_str=str(AttributeValueType.FILE),
            ).exclude(file_value__isnull=True).exclude(file_value='').order_by('id')

            for attribute in queryset.iterator():
                scanned += 1

                thumbnail_path = attribute.thumbnail_relative_path
                if not thumbnail_path:
                    unsupported += 1
                    continue

                supported += 1

                if attribute.has_thumbnail:
                    skipped_existing += 1
                    continue

                if dry_run:
                    would_generate += 1
                    continue

                was_generated = AttributeThumbnail(attribute).generate_thumbnail_best_effort()
                attribute.set_thumbnail_exists_cache(was_generated)
                if was_generated:
                    generated += 1
                else:
                    failed += 1

        summary = (
            'Thumbnail backfill summary: '
            f'scanned={scanned}, '
            f'supported={supported}, '
            f'unsupported={unsupported}, '
            f'skipped_existing={skipped_existing}, '
            f'generated={generated}, '
            f'failed={failed}, '
            f'would_generate={would_generate}'
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run mode enabled. No files were written.'))

        if failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))