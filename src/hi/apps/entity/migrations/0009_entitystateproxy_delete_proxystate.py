# Generated by Django 4.2.15 on 2024-10-07 15:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("entity", "0008_entityview_entity_view_entity_location_view"),
    ]

    operations = [
        migrations.CreateModel(
            name="EntityStateProxy",
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
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_state_proxies",
                        to="entity.entity",
                        verbose_name="Entity",
                    ),
                ),
                (
                    "entity_state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_state_proxies",
                        to="entity.entitystate",
                        verbose_name="Entity State",
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="ProxyState",
        ),
    ]
