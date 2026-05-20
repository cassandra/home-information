"""Rename sensor / sensor-history event-video fields to disambiguate
them from entity-level live-feed fields.

This migration performs ONLY field renames (no column drops or adds
beyond the one explicit ``AddField`` for the new
``provides_event_video_snapshot`` capability flag). Each rename
preserves the underlying column data — no data migration step is
needed.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sense", "0011_add_previous_integration_identity"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sensor",
            old_name="provides_video_stream",
            new_name="provides_event_video_clip",
        ),
        migrations.RenameField(
            model_name="sensorhistory",
            old_name="has_video_stream",
            new_name="has_event_video_clip",
        ),
        migrations.RenameField(
            model_name="sensorhistory",
            old_name="source_image_url",
            new_name="event_video_snapshot_url",
        ),
        migrations.AlterField(
            model_name="sensor",
            name="provides_event_video_clip",
            field=models.BooleanField(
                default=False,
                verbose_name="Provides Event Video Clip",
            ),
        ),
        migrations.AlterField(
            model_name="sensorhistory",
            name="has_event_video_clip",
            field=models.BooleanField(
                default=False,
                verbose_name="Has Event Video Clip",
            ),
        ),
        migrations.AlterField(
            model_name="sensorhistory",
            name="event_video_snapshot_url",
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name="Event Video Snapshot URL",
            ),
        ),
        migrations.AddField(
            model_name="sensor",
            name="provides_event_video_snapshot",
            field=models.BooleanField(
                default=False,
                verbose_name="Provides Event Video Snapshot",
            ),
        ),
    ]
