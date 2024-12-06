# Generated by Django 4.2.15 on 2024-12-06 15:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("event", "0005_alarmaction_created_datetime_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventclause",
            name="event_definition",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="event_clauses",
                to="event.eventdefinition",
                verbose_name="Event Definition",
            ),
        ),
    ]
