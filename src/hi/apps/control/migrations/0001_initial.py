# Generated by Django 4.2.15 on 2024-10-13 21:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("entity", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Controller",
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
                    "controller_type_str",
                    models.CharField(max_length=32, verbose_name="Controller Type"),
                ),
                (
                    "entity_state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="controllers",
                        to="entity.entitystate",
                        verbose_name="Entity State",
                    ),
                ),
            ],
            options={
                "verbose_name": "Controller",
                "verbose_name_plural": "Controllers",
            },
        ),
        migrations.CreateModel(
            name="ControllerHistory",
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
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "controller",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history",
                        to="control.controller",
                        verbose_name="Controller",
                    ),
                ),
            ],
            options={
                "verbose_name": "Controller History",
                "verbose_name_plural": "Controller History",
            },
        ),
    ]
