import logging
from contextlib import ExitStack, nullcontext
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from hi.apps.entity.models import Entity
from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.enums import IntegrationCapability
from hi.integrations.transient_models import IntegrationKey
from hi.services.homebox.hb_metadata import HbMetaData
from hi.services.homebox.connector.homebox_connector import HomeBoxConnector
from hi.testing.async_task_utils import AsyncTaskTestCase


logging.disable(logging.CRITICAL)


class TestHomeBoxConnector(SimpleTestCase):

    def _key(self, name: str) -> IntegrationKey:
        return IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name=name,
        )

    def test_sync_helper_uses_mocked_api_response_and_delegates_entity_sync(self):
        synchronizer = HomeBoxConnector()
        manager = Mock()
        manager.hb_client = object()
        manager.include_filter = ''
        manager.exclude_filter = ''
        manager.fetch_hb_items_from_api.return_value = [Mock(), Mock(), Mock()]

        with patch.object(synchronizer, 'hb_manager', return_value=manager), \
                patch.object(synchronizer, '_sync_helper_entities', return_value=[]) as sync_entities_mock:
            result = synchronizer._sync_impl(is_initial_connect=True)

        self.assertIsInstance(result, IntegrationSyncResult)
        self.assertIn('Found 3 current HomeBox items.', result.info_list)
        sync_entities_mock.assert_called_once_with(
            item_list=manager.fetch_hb_items_from_api.return_value,
            result=result,
            include_tokens=frozenset(),
            exclude_tokens=frozenset(),
        )

    def test_sync_helper_entities_create_update_remove_entities(self):
        synchronizer = HomeBoxConnector()
        result = IntegrationSyncResult(title='HomeBox Import Result')

        item_new = Mock(name='item_new')
        item_existing = Mock(name='item_existing')
        item_invalid = Mock(name='item_invalid')

        new_key = self._key('item-new')
        existing_key = self._key('item-existing')
        stale_key = self._key('item-stale')

        existing_entity = Mock(name='existing_entity')
        stale_entity = Mock(name='stale_entity')
        created_entity = Mock(name='created_entity')

        def key_from_item(hb_item):
            if hb_item is item_new:
                return new_key
            if hb_item is item_existing:
                return existing_key
            raise ValueError('missing id')

        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    'hi.services.homebox.connector.homebox_connector.transaction.atomic',
                    return_value=nullcontext(),
                )
            )
            stack.enter_context(
                patch(
                    'hi.services.homebox.connector.homebox_connector.HbConverter.hb_item_to_integration_key',
                    side_effect=key_from_item,
                )
            )
            stack.enter_context(
                patch.object(
                    synchronizer,
                    '_get_existing_hb_entities',
                    return_value={
                        existing_key: existing_entity,
                        stale_key: stale_entity,
                    },
                )
            )
            create_entity_mock = stack.enter_context(
                patch.object(
                    synchronizer,
                    '_create_entity',
                    return_value=created_entity,
                )
            )
            update_entity_mock = stack.enter_context(
                patch.object(synchronizer, '_update_entity')
            )
            remove_entity_mock = stack.enter_context(
                patch.object(synchronizer, '_remove_entity')
            )
            # Reconnect pre-pass (Issue #281) is framework-level on
            # IntegrationConnector.reconnect_disconnected_items and
            # does its own DB query; this SimpleTestCase doesn't allow
            # DB access, so stub it out. The reconnect logic itself
            # is covered by FindReconnectCandidatesTests in
            # test_entity_operations.py.
            stack.enter_context(
                patch.object(synchronizer, 'reconnect_disconnected_items')
            )

            synchronizer._sync_helper_entities(
                item_list=[item_new, item_existing, item_invalid],
                result=result,
            )

        create_entity_mock.assert_called_once_with(item=item_new, result=result)
        update_entity_mock.assert_called_once_with(
            entity=existing_entity,
            item=item_existing,
            result=result,
        )
        remove_entity_mock.assert_called_once_with(
            entity=stale_entity,
            result=result,
        )

        self.assertIn('Found 2 existing HomeBox items.', result.info_list)
        self.assertTrue(any('Ignoring HomeBox item due to missing/invalid id' in message
                            for message in result.error_list))

    def test_sync_helper_filters_items_and_populates_count(self):
        """When include/exclude tokens are present, ``_sync_helper_entities``
        rejects non-matching items, increments ``items_filtered_count``
        on the result, and sets the standard footer message."""
        synchronizer = HomeBoxConnector()
        result = IntegrationSyncResult(title='X')

        # Build minimal HbItem-like mocks: only the fields the
        # predicate reads + the archived/id used by the helper.
        from hi.services.homebox.hb_models import HbItem
        item_in = HbItem(api_dict={
            'id': '1',
            'name': 'In',
            'location': {'name': 'Garage'},
            'tags': [],
        })
        item_out = HbItem(api_dict={
            'id': '2',
            'name': 'Out',
            'location': {'name': 'Basement'},
            'tags': [],
        })

        with ExitStack() as stack:
            stack.enter_context(patch(
                'hi.services.homebox.connector.homebox_connector.transaction.atomic',
                return_value=nullcontext(),
            ))
            stack.enter_context(patch.object(
                synchronizer, '_get_existing_hb_entities', return_value={},
            ))
            stack.enter_context(patch.object(
                synchronizer, 'reconnect_disconnected_items',
            ))
            stack.enter_context(patch.object(
                synchronizer, '_create_entity', return_value=Mock(),
            ))

            synchronizer._sync_helper_entities(
                item_list=[item_in, item_out],
                result=result,
                include_tokens=frozenset({'garage'}),
                exclude_tokens=frozenset(),
            )

        self.assertEqual(result.items_filtered_count, 1)
        self.assertTrue(any('Filtered 1 item(s)' in message
                            for message in result.info_list))
        self.assertIn('Include Items By Location/Tag', result.footer_message)


class TestHomeBoxConnectorSyncImplCreatedEntities(SimpleTestCase):
    """HomeBoxConnector._sync_impl reports newly-created entities
    on result.created_entities. The framework caller does the
    grouping via the gateway (HomeBox inherits the by-EntityType
    default; with HbConverter currently stamping every item as
    OTHER, the operator sees a single 'Other' group)."""

    def test_sync_impl_populates_created_entities(self):
        synchronizer = HomeBoxConnector()
        manager = Mock()
        manager.hb_client = object()
        manager.include_filter = ''
        manager.exclude_filter = ''
        manager.fetch_hb_items_from_api.return_value = [Mock(), Mock()]

        entity_a = Mock()
        entity_a.name = 'Cordless Drill'
        entity_a.integration_key = IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name='item.42',
        )
        entity_a.id = 0
        entity_b = Mock()
        entity_b.name = 'Stud Finder'
        entity_b.integration_key = IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name='item.43',
        )
        entity_b.id = 0

        with patch.object(synchronizer, 'hb_manager', return_value=manager), \
             patch.object(synchronizer, '_sync_helper_entities',
                          return_value=[entity_a, entity_b]):
            result = synchronizer._sync_impl(is_initial_connect=True)

        # Created entities flow through to the framework caller, which
        # groups them via gateway.group_entities_for_placement.
        self.assertEqual(result.created_entities, [entity_a, entity_b])

    def test_sync_impl_emits_empty_when_no_items_imported(self):
        synchronizer = HomeBoxConnector()
        manager = Mock()
        manager.hb_client = object()
        manager.include_filter = ''
        manager.exclude_filter = ''
        manager.fetch_hb_items_from_api.return_value = []

        with patch.object(synchronizer, 'hb_manager', return_value=manager), \
                patch.object(synchronizer, '_sync_helper_entities', return_value=[]):
            result = synchronizer._sync_impl(is_initial_connect=True)

        # No newly-created entities → empty created_entities → framework
        # caller leaves placement_input as None.
        self.assertEqual(result.created_entities, [])
        self.assertIsNone(result.placement_input)


class TestHomeBoxConnectorRebuildIntegrationComponents(SimpleTestCase):
    """
    Issue #281: the per-integration ``_rebuild_integration_components``
    override is the only piece each synchronizer contributes to the
    framework-level reconnect path. This test verifies that
    HomeBoxConnector's override dispatches to ``HbEntityFactory`` with
    the existing-entity argument set. Framework-level behavior
    (find candidates, strip prefix, clear previous identity, update
    entity map, info_list note) is covered by tests of
    IntegrationConnector.reconnect_disconnected_items. End-to-end
    DB cycle is exercised in Phase 6.
    """

    def test_dispatches_to_converter_with_existing_entity(self):
        synchronizer = HomeBoxConnector()
        result = IntegrationSyncResult(title='HomeBox Test')
        existing_entity = Mock(name='existing_entity')
        upstream = Mock(name='hb_item')

        with patch(
                'hi.services.homebox.connector.homebox_connector.HbEntityFactory.create_models_for_hb_item'
        ) as mock_converter:
            synchronizer._rebuild_integration_components(
                entity=existing_entity,
                upstream=upstream,
                result=result,
            )

        mock_converter.assert_called_once_with(
            hb_item=upstream,
            capability=IntegrationCapability.CONNECT,
            entity=existing_entity,
        )


class TestHomeBoxConnectorCheckNeedsSync(AsyncTaskTestCase):
    """Issue #283 — sync-check probe shape for HomeBox.

    Uses a real DB so the probe's ``Entity.objects.filter(...)``
    query path is exercised end-to-end. Only the upstream HTTP
    boundary is mocked (the manager's
    ``fetch_hb_items_summary_from_api_async`` coroutine), which is
    the appropriate seam — internal accessors like
    ``_get_current_integration_keys`` run for real.

    Inherits ``AsyncTaskTestCase`` (a ``TransactionTestCase``
    subclass with a shared event loop) — required because the
    probe's ``sync_to_async`` DB query runs on a different thread
    than the test's transaction-wrapped writes, which deadlocks
    under SQLite when using a plain ``TestCase``.
    """

    def _hb_key(self, name: str):
        return IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name=name,
        )

    def _make_hb_entities(self, integration_names):
        for name in integration_names:
            Entity.objects.create(
                name=f'HomeBox Item {name}',
                entity_type_str='LIGHT',
                integration_id=HbMetaData.integration_id,
                integration_name=name,
            )

    def _run_check(self, summary_list, include_filter='', exclude_filter=''):
        synchronizer = HomeBoxConnector()
        manager = Mock()
        manager.include_filter = include_filter
        manager.exclude_filter = exclude_filter

        async def fetch_summary():
            return summary_list

        manager.fetch_hb_items_summary_from_api_async = fetch_summary

        async def get_manager():
            return manager

        with patch.object(synchronizer, 'hb_manager_async', side_effect=get_manager):
            return self.run_async(synchronizer.check_needs_sync())

    def test_in_sync_when_upstream_matches_hi(self):
        self._make_hb_entities(['1', '2'])
        delta = self._run_check(summary_list=[{'id': 1}, {'id': 2}])
        self.assertFalse(delta.needs_sync)

    def test_upstream_added_appears_in_delta(self):
        self._make_hb_entities(['1', '2'])
        delta = self._run_check(summary_list=[{'id': 1}, {'id': 2}, {'id': 3}])
        self.assertEqual(delta.added, {self._hb_key('3')})
        self.assertEqual(delta.removed, set())

    def test_upstream_removed_appears_in_delta(self):
        self._make_hb_entities(['1', '2'])
        delta = self._run_check(summary_list=[{'id': 1}])
        self.assertEqual(delta.added, set())
        self.assertEqual(delta.removed, {self._hb_key('2')})

    def test_summary_items_missing_id_are_skipped(self):
        # Defensive: a HomeBox item with no id (corrupted upstream
        # response) does not crash the probe — it is just dropped
        # from the upstream set.
        self._make_hb_entities(['1', '3'])
        delta = self._run_check(
            summary_list=[{'id': 1}, {'name': 'no-id'}, {'id': 3}],
        )
        self.assertFalse(delta.needs_sync)

    def test_returns_none_when_manager_not_ready(self):
        synchronizer = HomeBoxConnector()

        async def get_manager():
            return None

        with patch.object(synchronizer, 'hb_manager_async', side_effect=get_manager):
            result = self.run_async(synchronizer.check_needs_sync())

        self.assertIsNone(result)

    def test_other_integrations_entities_are_ignored(self):
        # An entity from a different integration must not pollute
        # the HI key set the HomeBox probe compares against.
        self._make_hb_entities(['1'])
        Entity.objects.create(
            name='Other Integration Entity',
            entity_type_str='LIGHT',
            integration_id='hass',
            integration_name='other.entity',
        )
        delta = self._run_check(summary_list=[{'id': 1}])
        self.assertFalse(delta.needs_sync)
