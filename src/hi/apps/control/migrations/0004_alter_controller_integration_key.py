# Generated by Django 4.2.15 on 2024-08-25 23:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("control", "0003_rename_integration_id_controller_integration_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="controller",
            name="integration_key",
            field=models.CharField(
                blank=True, max_length=128, null=True, verbose_name="Integration Key"
            ),
        ),
    ]
