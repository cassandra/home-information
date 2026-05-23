import logging

from django.db import migrations, models


def delete_homebox_orphan_attributes(apps, schema_editor):
    """Delete EntityAttribute rows for HomeBox-integrated entities.

    ``QuerySet.delete()`` here uses the historical model (field set
    only) — runtime signals and overridden ``delete()`` methods do
    not fire, so any on-disk file referenced by a deleted FILE-type
    row stays on disk."""
    logger = logging.getLogger('hi.apps.entity.migrations.0020')

    Entity = apps.get_model('entity', 'Entity')
    EntityAttribute = apps.get_model('entity', 'EntityAttribute')

    affected_entities = list(
        Entity.objects.filter(integration_id='hb').values_list('id', flat=True)
    )
    if not affected_entities:
        logger.info('HomeBox Connect migration: no HomeBox entities present.')
        return

    deleted_count, _ = EntityAttribute.objects.filter(
        entity_id__in=affected_entities,
    ).delete()

    logger.info(
        f'HomeBox Connect migration: deleted {deleted_count} EntityAttribute '
        f'row(s) across {len(affected_entities)} entit(y/ies). '
        f'Entity ids: {affected_entities}'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('entity', '0019_entity_video_snapshot_stream_fps'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entity',
            old_name='can_add_custom_attributes',
            new_name='allow_internal_attributes',
        ),
        migrations.AlterField(
            model_name='entity',
            name='allow_internal_attributes',
            field=models.BooleanField(default=True, verbose_name='Allow Internal Attributes?'),
        ),
        migrations.RunPython(
            code=delete_homebox_orphan_attributes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
