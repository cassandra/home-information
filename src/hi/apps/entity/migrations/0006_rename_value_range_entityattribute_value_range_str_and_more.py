# Generated by Django 4.2.15 on 2024-12-04 22:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("entity", "0005_entityattribute_value_range"),
    ]

    operations = [
        migrations.RenameField(
            model_name="entityattribute",
            old_name="value_range",
            new_name="value_range_str",
        ),
        migrations.RenameField(
            model_name="entitystate",
            old_name="value_range",
            new_name="value_range_str",
        ),
    ]
