# Generated by Django 4.2.15 on 2025-01-18 22:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="locationview",
            name="svg_style_name_str",
            field=models.CharField(
                default="greyscale", max_length=32, verbose_name="Style Name"
            ),
            preserve_default=False,
        ),
    ]
