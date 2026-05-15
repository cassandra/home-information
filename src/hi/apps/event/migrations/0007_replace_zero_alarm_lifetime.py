"""
Repair existing AlarmAction rows whose ``alarm_lifetime_secs`` was
set to zero by the previous "0 = until acknowledged" convention. The
alarm-queue layer never honored that intent — it treated zero as
"expires immediately", which made connectivity and battery alarms
silently vanish on creation.

The new contract (see ``Alarm.MAX_LIFETIME_SECS`` and
``Alarm.__post_init__``): use the explicit MAX value for
"effectively never expires"; zero is rejected at construction. This
migration normalizes any pre-existing zero rows to the same MAX so
their alarms behave correctly going forward.

Reverse path is intentionally a no-op — once normalized to MAX, the
original zero values are not preserved (they were broken anyway).
"""
from django.db import migrations


# Inlined to avoid importing from ``hi.apps.alert.alarm`` inside a
# migration: imports of app-level models from migrations are fragile
# during squash / rebuild cycles. This value must stay in sync with
# ``Alarm.MAX_LIFETIME_SECS``.
_MAX_LIFETIME_SECS = 365 * 24 * 60 * 60


def replace_zero_alarm_lifetime(apps, schema_editor):
    AlarmAction = apps.get_model('event', 'AlarmAction')
    AlarmAction.objects.filter(alarm_lifetime_secs=0).update(
        alarm_lifetime_secs=_MAX_LIFETIME_SECS,
    )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0006_add_previous_integration_identity'),
    ]

    operations = [
        migrations.RunPython(
            replace_zero_alarm_lifetime,
            noop_reverse,
        ),
    ]
