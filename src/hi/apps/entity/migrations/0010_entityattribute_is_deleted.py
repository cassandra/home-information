from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entity', '0009_entityattribute_order_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='entityattribute',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Deleted?'),
        ),
    ]
