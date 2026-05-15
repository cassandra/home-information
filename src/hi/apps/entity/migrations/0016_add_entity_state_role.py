from django.db import migrations, models


def populate_role_str(apps, schema_editor):
    # Backfill role_str on existing EntityStates with the
    # type-default role. New rows are populated at creation time by
    # EntityState.save() / factory paths.
    from hi.apps.entity.enums import EntityStateType
    EntityState = apps.get_model("entity", "EntityState")
    for state in EntityState.objects.filter(role_str=""):
        state_type = EntityStateType.from_name_safe(state.entity_state_type_str)
        state.role_str = str(state_type.default_role())
        state.save(update_fields=["role_str"])


class Migration(migrations.Migration):

    dependencies = [
        ("entity", "0015_add_previous_integration_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="entitystate",
            name="role_str",
            field=models.CharField(default="", max_length=64, verbose_name="Role"),
            preserve_default=False,
        ),
        migrations.RunPython(populate_role_str, migrations.RunPython.noop),
    ]
