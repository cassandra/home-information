# Generated by Django 4.2.15 on 2024-12-28 21:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "simulator",
            "0011_rename_entity_class_id_dbsimentity_entity_fields_class_id_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="dbsimentity",
            name="entity_fields_class_id",
            field=models.CharField(
                max_length=255, verbose_name="Entity Fields Class Id"
            ),
        ),
    ]
