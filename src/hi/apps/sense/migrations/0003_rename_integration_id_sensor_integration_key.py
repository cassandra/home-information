# Generated by Django 4.2.15 on 2024-08-25 23:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sense", "0002_sensor_integration_id_sensor_integration_type_str"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sensor",
            old_name="integration_id",
            new_name="integration_key",
        ),
    ]
