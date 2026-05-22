from django.db import migrations, models


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
    ]
