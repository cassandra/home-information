from django.db import migrations


def map_cameras_typed_to_security_view(apps, schema_editor):
    Collection = apps.get_model('collection', 'Collection')
    Collection.objects.filter(
        collection_type_str = 'CAMERAS',
    ).update(
        collection_view_type_str = 'SECURITY',
    )


def reverse_map_security_view_to_grid(apps, schema_editor):
    Collection = apps.get_model('collection', 'Collection')
    Collection.objects.filter(
        collection_type_str = 'CAMERAS',
        collection_view_type_str = 'SECURITY',
    ).update(
        collection_view_type_str = 'GRID',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0002_alter_collection_order_id_and_more'),
    ]

    operations = [
        migrations.RunPython(
            map_cameras_typed_to_security_view,
            reverse_code = reverse_map_security_view_to_grid,
        ),
    ]
