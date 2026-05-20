"""Replace ``SensorHistory.event_video_snapshot_url`` with a boolean
``has_event_video_snapshot`` flag.

The URL is no longer stored — gateways generate it on demand from
the event id (matching the existing pattern for event video clips).
This makes the snapshot affordance robust against integration
host-relocation: the operator's stored URLs no longer point at a
stale base_url after they move e.g. Frigate to a new host.

Migration shape:
  1. Add the ``has_event_video_snapshot`` column.
  2. Backfill: any row that previously stored a non-empty snapshot
     URL had a snapshot, so flag it as such.
  3. Drop the ``event_video_snapshot_url`` column.

Order matters — the backfill must run between the add and the drop.
"""
from django.db import migrations, models


def _backfill_has_event_video_snapshot(apps, schema_editor):
    SensorHistory = apps.get_model('sense', 'SensorHistory')
    SensorHistory.objects.exclude(
        event_video_snapshot_url__isnull=True,
    ).exclude(
        event_video_snapshot_url='',
    ).update(has_event_video_snapshot=True)


def _reverse_noop(apps, schema_editor):
    # The URL column is being dropped in the same migration, so we
    # have nowhere to write the URL back to on reverse. The flag
    # will simply be lost.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('sense', '0012_event_video_field_renames'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensorhistory',
            name='has_event_video_snapshot',
            field=models.BooleanField(
                default=False,
                verbose_name='Has Event Video Snapshot',
            ),
        ),
        migrations.RunPython(
            _backfill_has_event_video_snapshot,
            _reverse_noop,
        ),
        migrations.RemoveField(
            model_name='sensorhistory',
            name='event_video_snapshot_url',
        ),
    ]
