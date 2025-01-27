# Generated by Django 4.2.15 on 2025-01-27 18:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("entity", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Sensor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "integration_id",
                    models.CharField(
                        blank=True,
                        max_length=32,
                        null=True,
                        verbose_name="Integration Id",
                    ),
                ),
                (
                    "integration_name",
                    models.CharField(
                        blank=True,
                        max_length=128,
                        null=True,
                        verbose_name="Integration Name",
                    ),
                ),
                ("name", models.CharField(max_length=64, verbose_name="Name")),
                (
                    "sensor_type_str",
                    models.CharField(max_length=32, verbose_name="Sensor Type"),
                ),
                (
                    "persist_history",
                    models.BooleanField(default=True, verbose_name="Persist History"),
                ),
                (
                    "entity_state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sensors",
                        to="entity.entitystate",
                        verbose_name="Entity State",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sensor",
                "verbose_name_plural": "Sensors",
            },
        ),
        migrations.CreateModel(
            name="SensorHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.CharField(max_length=255, verbose_name="Value")),
                (
                    "details",
                    models.TextField(blank=True, null=True, verbose_name="Details"),
                ),
                (
                    "image_url",
                    models.TextField(blank=True, null=True, verbose_name="Image URL"),
                ),
                (
                    "response_datetime",
                    models.DateTimeField(db_index=True, verbose_name="Timestamp"),
                ),
                (
                    "sensor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history",
                        to="sense.sensor",
                        verbose_name="Sensor",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sensor History",
                "verbose_name_plural": "Sensor History",
                "ordering": ["-response_datetime"],
                "indexes": [
                    models.Index(
                        fields=["sensor", "-response_datetime"],
                        name="sense_senso_sensor__e2513c_idx",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="sensor",
            constraint=models.UniqueConstraint(
                fields=("integration_id", "integration_name"),
                name="sensor_integration_key",
            ),
        ),
    ]
