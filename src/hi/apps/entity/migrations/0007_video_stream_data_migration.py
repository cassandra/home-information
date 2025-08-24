# Data migration for Issue #106 - VideoStream Infrastructure Refactor
# Migrates existing data from VIDEO_STREAM EntityStates to new VideoStream model

from django.db import migrations


def migrate_video_stream_data(apps, schema_editor):
    """
    Migrate existing VIDEO_STREAM data to new VideoStream infrastructure:
    1. Set has_video_stream=True for ZoneMinder camera entities
    2. Set provides_video_stream=True for MOVEMENT sensors in ZM entities
    3. Delete VIDEO_STREAM sensors
    4. Delete VIDEO_STREAM EntityStates
    """
    Entity = apps.get_model('entity', 'Entity')
    EntityState = apps.get_model('entity', 'EntityState')
    Sensor = apps.get_model('sense', 'Sensor')
    
    # 1. Update ZoneMinder camera entities to have video capability
    zm_cameras = Entity.objects.filter(
        integration_id='zm',
        entity_type_str='camera'  # Lowercase string value per LabeledEnum
    )
    updated_count = zm_cameras.update(has_video_stream=True)
    print(f"Updated {updated_count} ZoneMinder camera entities with has_video_stream=True")
    
    # 2. Update MOVEMENT sensors for ZM entities to provide video streams
    movement_sensors = Sensor.objects.filter(
        entity_state__entity_state_type_str='movement',  # Lowercase string value
        entity_state__entity__integration_id='zm'
    )
    sensor_count = movement_sensors.update(provides_video_stream=True)
    print(f"Updated {sensor_count} MOVEMENT sensors with provides_video_stream=True")
    
    # 3. Delete VIDEO_STREAM sensors (CASCADE will handle SensorHistory)
    video_stream_sensors = Sensor.objects.filter(
        entity_state__entity_state_type_str='video_stream'  # Lowercase string value
    )
    video_sensor_count = video_stream_sensors.count()
    if video_sensor_count > 0:
        video_stream_sensors.delete()
        print(f"Deleted {video_sensor_count} VIDEO_STREAM sensors")
    
    # 4. Delete VIDEO_STREAM EntityStates (CASCADE will handle delegations)
    video_stream_states = EntityState.objects.filter(
        entity_state_type_str='video_stream'  # Lowercase string value
    )
    video_state_count = video_stream_states.count()
    if video_state_count > 0:
        video_stream_states.delete()
        print(f"Deleted {video_state_count} VIDEO_STREAM EntityStates")
    
    # Summary
    print(f"Migration complete: {updated_count} cameras updated, "
          f"{sensor_count} sensors updated, "
          f"{video_sensor_count} video sensors deleted, "
          f"{video_state_count} video states deleted")


def reverse_migration(apps, schema_editor):
    """
    This migration cannot be reversed because:
    1. VIDEO_STREAM enum value no longer exists in the code
    2. Deleted data cannot be reconstructed programmatically
    """
    raise NotImplementedError(
        "This migration cannot be reversed. The VIDEO_STREAM EntityStateType "
        "no longer exists and deleted data cannot be reconstructed."
    )


class Migration(migrations.Migration):
    
    dependencies = [
        ('entity', '0006_entity_has_video_stream'),
        ('sense', '0005_sensor_provides_video_stream'),
    ]
    
    operations = [
        migrations.RunPython(
            migrate_video_stream_data,
            reverse_migration
        ),
    ]
