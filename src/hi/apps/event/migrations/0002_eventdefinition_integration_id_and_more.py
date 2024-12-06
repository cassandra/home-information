# Generated by Django 4.2.15 on 2024-12-05 22:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("event", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventdefinition",
            name="integration_id",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="Integration Id"
            ),
        ),
        migrations.AddField(
            model_name="eventdefinition",
            name="integration_name",
            field=models.CharField(
                blank=True, max_length=128, null=True, verbose_name="Integration Name"
            ),
        ),
    ]
