# Generated by Django 4.2.15 on 2025-01-27 18:15

from django.db import migrations, models
import django.db.models.deletion
import hi.apps.common.svg_models
import hi.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Location",
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
                ("name", models.CharField(max_length=64, verbose_name="Name")),
                (
                    "svg_fragment_filename",
                    models.CharField(max_length=255, verbose_name="SVG Filename"),
                ),
                (
                    "svg_view_box_str",
                    models.CharField(max_length=128, verbose_name="Viewbox"),
                ),
                (
                    "order_id",
                    models.PositiveIntegerField(
                        db_index=True, default=0, verbose_name="Order Id"
                    ),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "updated_datetime",
                    models.DateTimeField(auto_now=True, verbose_name="Updated"),
                ),
            ],
            options={
                "verbose_name": "Location",
                "verbose_name_plural": "Locations",
                "ordering": ["order_id"],
            },
            bases=(models.Model, hi.models.ItemTypeModelMixin),
        ),
        migrations.CreateModel(
            name="LocationView",
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
                    "location_view_type_str",
                    models.CharField(max_length=32, verbose_name="View Type"),
                ),
                ("name", models.CharField(max_length=64, verbose_name="Name")),
                (
                    "svg_view_box_str",
                    models.CharField(max_length=128, verbose_name="Viewbox"),
                ),
                (
                    "svg_rotate",
                    hi.apps.common.svg_models.SvgDecimalField(
                        decimal_places=6, max_digits=11, verbose_name="Rotate"
                    ),
                ),
                (
                    "svg_style_name_str",
                    models.CharField(max_length=32, verbose_name="Style"),
                ),
                (
                    "order_id",
                    models.PositiveIntegerField(
                        db_index=True, default=0, verbose_name="Order Id"
                    ),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "updated_datetime",
                    models.DateTimeField(auto_now=True, verbose_name="Updated"),
                ),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="views",
                        to="location.location",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "View",
                "verbose_name_plural": "Views",
                "ordering": ["order_id"],
            },
            bases=(models.Model, hi.models.ItemTypeModelMixin),
        ),
        migrations.CreateModel(
            name="LocationAttribute",
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
                ("name", models.CharField(max_length=64, verbose_name="Name")),
                (
                    "value",
                    models.TextField(blank=True, null=True, verbose_name="Value"),
                ),
                (
                    "file_value",
                    models.FileField(blank=True, null=True, upload_to="attributes/"),
                ),
                (
                    "file_mime_type",
                    models.CharField(
                        blank=True, max_length=128, null=True, verbose_name="Mime Type"
                    ),
                ),
                (
                    "value_type_str",
                    models.CharField(max_length=32, verbose_name="Value Type"),
                ),
                (
                    "value_range_str",
                    models.TextField(blank=True, null=True, verbose_name="Value Range"),
                ),
                (
                    "integration_key_str",
                    models.CharField(
                        blank=True,
                        max_length=128,
                        null=True,
                        verbose_name="Integration Key",
                    ),
                ),
                (
                    "attribute_type_str",
                    models.CharField(max_length=32, verbose_name="Attribute Type"),
                ),
                (
                    "is_editable",
                    models.BooleanField(default=True, verbose_name="Editable?"),
                ),
                (
                    "is_required",
                    models.BooleanField(default=False, verbose_name="Required?"),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "updated_datetime",
                    models.DateTimeField(auto_now=True, verbose_name="Updated"),
                ),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attributes",
                        to="location.location",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Attribute",
                "verbose_name_plural": "Attributes",
                "indexes": [
                    models.Index(
                        fields=["name", "value"], name="location_lo_name_0c26e1_idx"
                    )
                ],
            },
        ),
    ]
