import logging

from django.db import migrations, models


def backfill_data_source(apps, schema_editor):
    """Mark integration-attached entities that disallow internal
    attributes as EXTERNAL. All others keep the column default
    (INTERNAL). Today this affects only HomeBox-Connect entities."""
    logger = logging.getLogger('hi.apps.entity.migrations.0021')

    Entity = apps.get_model('entity', 'Entity')

    updated = Entity.objects.filter(
        integration_id__isnull=False,
        allow_internal_attributes=False,
    ).exclude(
        integration_id='',
    ).update(
        data_source_str='external',
    )

    logger.info(
        f'EntityDataSource backfill: marked {updated} entity row(s) EXTERNAL.'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('entity', '0020_entity_allow_internal_attributes'),
    ]

    operations = [
        migrations.AddField(
            model_name='entity',
            name='data_source_str',
            field=models.CharField(
                default='internal',
                max_length=16,
                verbose_name='Data Source',
            ),
        ),
        migrations.RunPython(
            code=backfill_data_source,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
