import logging

from django.db import migrations, models, transaction


def delete_homebox_orphan_attributes(apps, schema_editor):
    """Delete EntityAttribute rows for HomeBox-integrated entities.

    ``QuerySet.delete()`` here uses the historical model (field set
    only) — runtime signals and overridden ``delete()`` methods do
    not fire, so any on-disk file referenced by a deleted FILE-type
    row stays on disk."""
    logger = logging.getLogger('hi.apps.entity.migrations.0020')

    Entity = apps.get_model('entity', 'Entity')
    EntityAttribute = apps.get_model('entity', 'EntityAttribute')

    deleted_per_entity = []
    for entity in Entity.objects.filter(integration_id='hb').iterator():
        with transaction.atomic():
            qs = EntityAttribute.objects.filter(entity=entity)
            count = qs.count()
            if count == 0:
                continue
            qs.delete()
            deleted_per_entity.append((entity.id, count))

    if deleted_per_entity:
        total = sum(count for _id, count in deleted_per_entity)
        logger.info(
            f'HomeBox Connect migration: deleted {total} EntityAttribute '
            f'row(s) across {len(deleted_per_entity)} entit(y/ies). '
            f'Details: {deleted_per_entity}'
        )
    else:
        logger.info('HomeBox Connect migration: no EntityAttribute rows to delete.')


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
