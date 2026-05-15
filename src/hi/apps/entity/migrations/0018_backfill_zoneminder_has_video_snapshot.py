from django.db import migrations


def backfill_zoneminder_camera_snapshot_flag(apps, schema_editor):
    """Set has_video_snapshot=True for existing ZoneMinder camera
    entities. ZM monitors natively provide a still-image URL via
    ``nph-zms?mode=single``; the gateway's get_entity_video_snapshot
    override exposes that capability. Existing entities (imported
    before this field existed) need their flag flipped once via this
    backfill; future sync runs set the flag at create-time.

    Filters on ``has_video_stream=True`` rather than entity_type to
    survive user reclassification: entity_type is user-mutable after
    import, but ``has_video_stream`` is integration-owned and only set
    by the ZM sync path, so it stays a reliable proxy for "this entity
    is backed by a ZM monitor."
    """
    Entity = apps.get_model('entity', 'Entity')

    zm_cameras = Entity.objects.filter(
        integration_id='zm',
        has_video_stream=True,
    )
    updated = zm_cameras.update(has_video_snapshot=True)
    print(f'Backfilled has_video_snapshot=True on {updated} ZoneMinder camera entities')


def reverse_backfill(apps, schema_editor):
    Entity = apps.get_model('entity', 'Entity')

    reverted = Entity.objects.filter(
        integration_id='zm',
        has_video_stream=True,
        has_video_snapshot=True,
    ).update(has_video_snapshot=False)
    print(f'Reverted has_video_snapshot=False on {reverted} ZoneMinder camera entities')


class Migration(migrations.Migration):

    dependencies = [
        ('entity', '0017_entity_has_video_snapshot'),
    ]

    operations = [
        migrations.RunPython(
            backfill_zoneminder_camera_snapshot_flag,
            reverse_backfill,
        ),
    ]
