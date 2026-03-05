from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('location', '0004_locationattribute_order_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='locationattribute',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Deleted?'),
        ),
    ]
