# Generated by Django 4.2.15 on 2024-09-01 04:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("location", "0004_rename_svg_viewbox_location_svg_view_box_str_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="locationview",
            old_name="svg_rotation",
            new_name="svg_rotate",
        ),
    ]
