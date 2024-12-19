# Generated by Django 4.2.15 on 2024-12-19 02:51

from django.db import migrations, models
import django.db.models.deletion
import hi.apps.common.svg_models
import hi.apps.location.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("location", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Entity",
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
                    "integration_id",
                    models.CharField(
                        blank=True,
                        max_length=32,
                        null=True,
                        verbose_name="Integration Id",
                    ),
                ),
                (
                    "integration_name",
                    models.CharField(
                        blank=True,
                        max_length=128,
                        null=True,
                        verbose_name="Integration Name",
                    ),
                ),
                ("name", models.CharField(max_length=64, verbose_name="Name")),
                (
                    "entity_type_str",
                    models.CharField(max_length=32, verbose_name="Entity Type"),
                ),
                (
                    "can_user_delete",
                    models.BooleanField(default=True, verbose_name="User Delete?"),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
            ],
            options={
                "verbose_name": "Entity",
                "verbose_name_plural": "Entities",
            },
            bases=(models.Model, hi.apps.location.models.LocationItemModelMixin),
        ),
        migrations.CreateModel(
            name="EntityState",
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
                    "entity_state_type_str",
                    models.CharField(
                        db_index=True, max_length=32, verbose_name="State Type"
                    ),
                ),
                ("name", models.CharField(max_length=64, verbose_name="Name")),
                (
                    "value_range_str",
                    models.TextField(blank=True, null=True, verbose_name="Value Range"),
                ),
                (
                    "units",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="Units"
                    ),
                ),
                (
                    "created_datetime",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created"),
                ),
                (
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="states",
                        to="entity.entity",
                        verbose_name="Entity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity State",
                "verbose_name_plural": "Entity States",
            },
        ),
        migrations.CreateModel(
            name="EntityView",
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
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_views",
                        to="entity.entity",
                        verbose_name="Entity",
                    ),
                ),
                (
                    "location_view",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_views",
                        to="location.locationview",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity View",
                "verbose_name_plural": "Entity Views",
            },
        ),
        migrations.CreateModel(
            name="EntityStateDelegation",
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
                    "delegate_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_state_delegations",
                        to="entity.entity",
                        verbose_name="Deleage Entity",
                    ),
                ),
                (
                    "entity_state",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_state_delegations",
                        to="entity.entitystate",
                        verbose_name="Entity State",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity State Delegation",
                "verbose_name_plural": "Entity State Delegations",
            },
        ),
        migrations.CreateModel(
            name="EntityPosition",
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
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="positions",
                        to="entity.entity",
                        verbose_name="Entity",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_positions",
                        to="location.location",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity Position",
                "verbose_name_plural": "Entity Positions",
            },
        ),
        migrations.CreateModel(
            name="EntityPath",
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
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="paths",
                        to="entity.entity",
                        verbose_name="Entity",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_paths",
                        to="location.location",
                        verbose_name="Location",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity Path",
                "verbose_name_plural": "Entity Paths",
            },
        ),
        migrations.CreateModel(
            name="EntityAttribute",
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
                    "entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attributes",
                        to="entity.entity",
                        verbose_name="Entity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Attribute",
                "verbose_name_plural": "Attributes",
            },
        ),
        migrations.AddConstraint(
            model_name="entity",
            constraint=models.UniqueConstraint(
                fields=("integration_id", "integration_name"),
                name="entity_integration_key",
            ),
        ),
        migrations.AddConstraint(
            model_name="entityview",
            constraint=models.UniqueConstraint(
                fields=("entity", "location_view"),
                name="entity_view_entity_location_view",
            ),
        ),
        migrations.AddConstraint(
            model_name="entitystatedelegation",
            constraint=models.UniqueConstraint(
                fields=("delegate_entity", "entity_state"),
                name="entity_state_delegation_uniqueness",
            ),
        ),
        migrations.AddConstraint(
            model_name="entityposition",
            constraint=models.UniqueConstraint(
                fields=("location", "entity"), name="entity_position_location_entity"
            ),
        ),
        migrations.AddConstraint(
            model_name="entitypath",
            constraint=models.UniqueConstraint(
                fields=("location", "entity"), name="entity_path_location_entity"
            ),
        ),
        migrations.AddIndex(
            model_name="entityattribute",
            index=models.Index(
                fields=["name", "value"], name="entity_enti_name_ca029b_idx"
            ),
        ),
    ]
