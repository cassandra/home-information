"""
Tests for the framework-default sync preview
(``IntegrationSyncPreviewer.build_from_check``).

Covers how a ``SyncDelta`` becomes preview category items: upstream
additions carry only their integration key; HI-side removals carry
the entity name plus key, bucketed into removed vs. detached by the
same user-data classifier the real sync uses.
"""
import logging

from django.test import TestCase

from hi.apps.attribute.enums import AttributeType
from hi.apps.entity.models import Entity, EntityAttribute
from hi.integrations.connector.sync_check import SyncDelta
from hi.integrations.connector.sync_preview import IntegrationSyncPreviewer
from hi.integrations.connector.sync_result import IntegrationSyncItem
from hi.integrations.transient_models import IntegrationKey

logging.disable(logging.CRITICAL)


def _key(name: str) -> IntegrationKey:
    return IntegrationKey(integration_id='test_integration', integration_name=name)


class IntegrationSyncPreviewerTests(TestCase):

    def _build_preview(self, delta, preserve_user_data=True):
        async def check_needs_sync():
            return delta

        return IntegrationSyncPreviewer.build_from_check(
            check_needs_sync_callable=check_needs_sync,
            result_title='Preview',
            preserve_user_data=preserve_user_data,
        )

    def _create_entity(self, name, integration_name, with_user_data=False):
        entity = Entity.objects.create(
            name=name,
            entity_type_str='LIGHT',
            integration_id='test_integration',
            integration_name=integration_name,
        )
        if with_user_data:
            EntityAttribute.objects.create(
                entity=entity,
                name='Notes',
                value='operator note',
                attribute_type_str=str(AttributeType.CUSTOM),
            )
        return entity

    def test_added_items_carry_key_without_name(self):
        result = self._build_preview(SyncDelta(added={_key('b'), _key('a')}))

        self.assertEqual(
            result.created_list,
            [
                IntegrationSyncItem(name='', integration_key=_key('a')),
                IntegrationSyncItem(name='', integration_key=_key('b')),
            ],
        )

    def test_removed_items_carry_name_and_key_bucketed_by_user_data(self):
        self._create_entity('Old Keypad', 'insteon:23.d0.86')
        self._create_entity('Porch Motion', 'insteon:2d.68.be', with_user_data=True)

        result = self._build_preview(SyncDelta(
            removed={_key('insteon:23.d0.86'), _key('insteon:2d.68.be')},
        ))

        self.assertEqual(
            result.removed_list,
            [IntegrationSyncItem(name='Old Keypad', integration_key=_key('insteon:23.d0.86'))],
        )
        self.assertEqual(
            result.detached_list,
            [IntegrationSyncItem(name='Porch Motion', integration_key=_key('insteon:2d.68.be'))],
        )

    def test_remove_all_policy_puts_user_data_entities_in_removed(self):
        self._create_entity('Porch Motion', 'insteon:2d.68.be', with_user_data=True)

        result = self._build_preview(
            SyncDelta(removed={_key('insteon:2d.68.be')}),
            preserve_user_data=False,
        )

        self.assertEqual(
            [item.name for item in result.removed_list],
            ['Porch Motion'],
        )
        self.assertEqual(result.detached_list, [])
