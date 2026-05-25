import logging

from django.db import migrations, models


def backfill_data_source(apps, schema_editor):
    """Mark every integration-attached entity as EXTERNAL. Native
    entities (no integration_id) keep the column default (INTERNAL).

    Semantics: data_source=EXTERNAL means data is actively being
    sourced from an upstream system. All Connect-mode integrations
    (HA, ZM, Frigate, HomeBox-Connect) mirror upstream — every
    integration-attached entity at the moment of this migration is
    Connect-mode (Import capability arrives in #358), so EXTERNAL
    is the correct value across the board.
    """
    logger = logging.getLogger('hi.apps.entity.migrations.0021')

    Entity = apps.get_model('entity', 'Entity')

    updated = Entity.objects.filter(
        integration_id__isnull=False,
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
