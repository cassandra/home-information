# Generated by Django 4.2.15 on 2024-12-19 02:51

from django.db import migrations, models
import django.db.models.deletion
import hi.apps.common.svg_models
import hi.apps.location.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("entity", "0001_initial"),
        ("location", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Collection",
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
                    "collection_type_str",
                    models.CharField(max_length=32, verbose_name="Collection Type"),
                ),
                (
                    "collection_view_type_str",
                    models.CharField(max_length=32, verbose_name="View Type"),
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
            ],
            options={
                "verbose_name": "Collection",
                "verbose_name_plural": "Collections",
                "ordering": ["order_id"],
            },
            bases=(models.Model, hi.apps.location.models.LocationItemModelMixin),
        ),
        migrations.CreateModel(
            name="CollectionView",
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
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collection_views",
                        to="collection.collection",
                        verbose_name="Collection",
                    ),
                ),
                (
                    "location_view",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collection_views",
                        to="location.locationview",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Collection View",
                "verbose_name_plural": "Collection Views",
            },
        ),
        migrations.CreateModel(
            name="CollectionPosition",
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
                    "svg_x",
                    hi.apps.common.svg_models.SvgDecimalField(
                        decimal_places=6, max_digits=11, verbose_name="X"
                    ),
                ),
                (
                    "svg_y",
                    hi.apps.common.svg_models.SvgDecimalField(
                        decimal_places=6, max_digits=11, verbose_name="Y"
                    ),
                ),
                (
                    "svg_scale",
                    hi.apps.common.svg_models.SvgDecimalField(
                        decimal_places=6,
                        default=1.0,
                        max_digits=11,
                        verbose_name="Scale",
                    ),
                ),
                (
                    "svg_rotate",
                    hi.apps.common.svg_models.SvgDecimalField(
                        decimal_places=6,
                        default=0.0,
                        max_digits=11,
                        verbose_name="Rotate",
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
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="positions",
                        to="collection.collection",
                        verbose_name="Collection",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collection_positions",
                        to="location.location",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Collection Position",
                "verbose_name_plural": "Collection Positions",
            },
        ),
        migrations.CreateModel(
            name="CollectionPath",
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
                ("svg_path", models.TextField(verbose_name="Path")),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "updated_datetime",
                    models.DateTimeField(auto_now=True, verbose_name="Updated"),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="paths",
                        to="collection.collection",
                        verbose_name="Collection",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collection_paths",
                        to="location.location",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Collection Path",
                "verbose_name_plural": "Collection Paths",
            },
        ),
        migrations.CreateModel(
            name="CollectionEntity",
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
                    "order_id",
                    models.PositiveIntegerField(default=0, verbose_name="Order Id"),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entities",
                        to="collection.collection",
                        verbose_name="Collection",
                    ),
                ),
                (
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collections",
                        to="entity.entity",
                        verbose_name="Entity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Collection Entity",
                "verbose_name_plural": "Collection Entities",
                "ordering": ["order_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="collectionposition",
            constraint=models.UniqueConstraint(
                fields=("location", "collection"),
                name="collection_position_location_entity",
            ),
        ),
        migrations.AddConstraint(
            model_name="collectionpath",
            constraint=models.UniqueConstraint(
                fields=("location", "collection"),
                name="collection_path_location_collection",
            ),
        ),
        migrations.AddIndex(
            model_name="collectionentity",
            index=models.Index(
                fields=["collection", "entity"], name="collection__collect_04e3d8_idx"
            ),
        ),
    ]
