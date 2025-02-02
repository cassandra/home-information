# Generated by Django 4.2.15 on 2025-02-02 16:19

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SimProfile",
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
                    "name",
                    models.CharField(max_length=128, unique=True, verbose_name="Name"),
                ),
                (
                    "last_switched_to_datetime",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="Last Switched To",
                    ),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
            ],
            options={
                "verbose_name": "Simulator Profile",
                "verbose_name_plural": "Simulator Profiles",
                "ordering": ["-last_switched_to_datetime"],
            },
        ),
        migrations.CreateModel(
            name="DbSimEntity",
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
                    "simulator_id",
                    models.CharField(max_length=64, verbose_name="Simulator Id"),
                ),
                (
                    "entity_fields_class_id",
                    models.CharField(
                        max_length=255, verbose_name="Entity Fields Class Id"
                    ),
                ),
                (
                    "sim_entity_type_str",
                    models.CharField(max_length=32, verbose_name="Entity Type"),
                ),
                (
                    "sim_entity_fields_json",
                    models.JSONField(default=dict, verbose_name="Entity Fields"),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "updated_datetime",
                    models.DateTimeField(auto_now=True, verbose_name="Updated"),
                ),
                (
                    "sim_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="db_sim_entities",
                        to="simulator.simprofile",
                        verbose_name="Simulator Profile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Simulator Entity",
                "verbose_name_plural": "Simulator Entities",
            },
        ),
    ]
