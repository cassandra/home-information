# Generated by Django 4.2.15 on 2024-10-11 15:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0011_alter_locationview_svg_view_box_str"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="location",
            name="svg_filename",
        ),
    ]
