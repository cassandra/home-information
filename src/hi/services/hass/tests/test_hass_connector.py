import json
import logging
import os
from unittest.mock import Mock, patch
from django.test import TestCase

from hi.apps.entity.models import Entity
from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from hi.services.hass.hass_connector import HassConnector
from hi.services.hass.hass_models import HassState
from hi.services.hass.integration import HassGateway

logging.disable(logging.CRITICAL)


class TestHassConnectorInitialization(TestCase):
    """Test HassConnector initialization and basic setup"""
    
    def test_init_creates_instance_successfully(self):
        """Test HassConnector initialization"""
        synchronizer = HassConnector()
        self.assertIsInstance(synchronizer, HassConnector)
    
    def test_synchronization_lock_name_constant(self):
        """All integration synchronizers share a single process-wide
        sync lock name; the base class declares it and subclasses do
        not override."""
        self.assertEqual(HassConnector.SYNCHRONIZATION_LOCK_NAME, 'integrations_sync')
    
    def test_inherits_from_mixins(self):
        """Test that HassConnector inherits from required mixins"""
        synchronizer = HassConnector()

        # Should inherit from HassMixin
        self.assertTrue(hasattr(synchronizer, 'hass_manager'))


class TestHassConnectorSyncMethod(TestCase):
    """Test main sync() method with database transactions"""
    
    def setUp(self):
        self.synchronizer = HassConnector()
    
    @patch('hi.integrations.connector.integration_connector.ExclusionLockContext')
    @patch.object(HassConnector, '_sync_impl')
    def test_sync_handles_runtime_error(self, mock_sync_impl, mock_lock_context):
        """Test sync method handles RuntimeError exceptions"""
        # Mock RuntimeError in sync helper
        mock_sync_impl.side_effect = RuntimeError("Database connection failed")
        
        # Mock lock context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock()
        mock_context.__exit__ = Mock(return_value=False)
        mock_lock_context.return_value = mock_context
        
        result = self.synchronizer.sync(is_initial_connect=True)
        
        # Verify error handling
        self.assertIn('Database connection failed', result.error_list[0])
    
    @patch('hi.integrations.connector.integration_connector.ExclusionLockContext')
    @patch.object(HassConnector, '_sync_impl')
    def test_sync_returns_error_result_on_exception(self, mock_sync_impl, mock_lock_context):
        """Test sync method returns proper error result when _sync_impl raises exception"""
        # Mock RuntimeError in sync helper
        mock_sync_impl.side_effect = RuntimeError("Database connection failed")
        
        # Mock lock context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock()
        mock_context.__exit__ = Mock(return_value=False)
        mock_lock_context.return_value = mock_context
        
        result = self.synchronizer.sync(is_initial_connect=True)
        
        # Verify actual error result structure and content
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Database connection failed', result.error_list[0])
        self.assertEqual(len(result.info_list), 0)  # No success messages on error


class TestHassConnectorSyncHelper(TestCase):
    """Test _sync_impl method logic"""
    
    def setUp(self):
        self.synchronizer = HassConnector()
        
        # Mock hass_manager and dependencies
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.mock_manager.include_filter = None


class TestHassConnectorStateConversion(TestCase):
    """Test HassConnector with real HASS API data"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Load real HASS API response data
        test_data_dir = os.path.join(os.path.dirname(__file__), 'data')
        try:
            with open(os.path.join(test_data_dir, 'hass-states.json'), 'r') as f:
                cls.real_hass_states_data = json.load(f)
        except FileNotFoundError:
            cls.real_hass_states_data = []
    
    def setUp(self):
        self.synchronizer = HassConnector()
    
    def test_real_data_entity_id_diversity(self):
        """Test that real HASS data contains diverse entity types for comprehensive testing"""
        if not self.real_hass_states_data:
            self.skipTest("No real HASS data available for testing")
        
        entity_ids = [entity['entity_id'] for entity in self.real_hass_states_data]
        
        # Extract domains
        domains = set()
        for entity_id in entity_ids:
            if '.' in entity_id:
                domain = entity_id.split('.', 1)[0]
                domains.add(domain)
        
        # Verify diverse entity types for sync testing
        expected_domains = ['camera', 'sensor', 'script']
        for expected_domain in expected_domains:
            self.assertIn(expected_domain, domains, 
                          f"Should have {expected_domain} entities for sync testing")
        
        # Verify substantial data for comprehensive sync testing
        self.assertGreaterEqual(len(entity_ids), 10, "Should have substantial entities for sync testing")


class TestHassConnectorTransactionBehavior(TestCase):
    """Test transaction handling and atomicity in sync operations"""
    
    def setUp(self):
        self.synchronizer = HassConnector()
    
    def test_sync_impl_executes_entity_operations_atomically(self):
        """Test that all entity operations in sync_helper execute within single transaction"""
        with patch.object(self.synchronizer, 'hass_manager') as mock_hass_manager, \
             patch.object(self.synchronizer, '_get_existing_hass_entities') as mock_get_entities, \
             patch.object(self.synchronizer, '_create_entity') as mock_create, \
             patch.object(self.synchronizer, '_remove_entity') as mock_remove:
            
            # Setup manager
            mock_manager = Mock()
            mock_manager.hass_client = Mock()
            mock_manager.include_filter = None
            mock_hass_manager.return_value = mock_manager

            # Setup scenario: one new device, one entity to remove
            api_states = {'light.new': self._create_mock_hass_state('light.new', 'light', 'on')}
            mock_manager.fetch_hass_states_from_api.return_value = api_states
            
            old_entity = Mock(spec=Entity)
            old_key = IntegrationKey(integration_id='hass', integration_name='old_device')
            mock_get_entities.return_value = {old_key: old_entity}
            
            # Track transaction usage
            with patch('hi.services.hass.hass_connector.transaction.atomic') as mock_atomic:
                mock_atomic.return_value.__enter__ = Mock()
                mock_atomic.return_value.__exit__ = Mock()
                
                result = self.synchronizer._sync_impl(is_initial_connect=True)
                
                # Verify atomic transaction was used exactly once
                mock_atomic.assert_called_once()
                
                # Verify both operations occurred (would be within same transaction)
                mock_create.assert_called_once()
                mock_remove.assert_called_once()
                
                # Verify successful result
                self.assertEqual(len(result.error_list), 0)
    
    def test_sync_impl_rollback_behavior_on_entity_operation_failure(self):
        """Test that transaction rollback works when entity operations fail"""
        with patch.object(self.synchronizer, 'hass_manager') as mock_hass_manager, \
             patch.object(self.synchronizer, '_get_existing_hass_entities') as mock_get_entities:
            
            # Setup manager
            mock_manager = Mock()
            mock_manager.hass_client = Mock()
            mock_manager.include_filter = None
            mock_hass_manager.return_value = mock_manager

            # Setup API data
            api_states = {'light.test': self._create_mock_hass_state('light.test', 'light', 'on')}
            mock_manager.fetch_hass_states_from_api.return_value = api_states
            mock_get_entities.return_value = {}
            
            # Mock entity creation failure within transaction
            with patch.object(self.synchronizer, '_create_entity') as mock_create:
                mock_create.side_effect = Exception("Entity creation failed")
                
                # Transaction should propagate the exception (allowing rollback)
                with self.assertRaises(Exception) as context:
                    self.synchronizer._sync_impl(is_initial_connect=True)
                
                self.assertEqual(str(context.exception), "Entity creation failed")
    
    def _create_mock_hass_state(self, entity_id, domain, state):
        """Helper to create mock HASS state for testing"""
        hass_state = Mock(spec=HassState)
        hass_state.entity_id = entity_id
        hass_state.domain = domain
        hass_state.state_value = state
        hass_state.entity_name_sans_prefix = entity_id.split('.', 1)[1]
        hass_state.entity_name_sans_suffix = hass_state.entity_name_sans_prefix
        hass_state.device_group_id = None
        hass_state.attributes = {}
        hass_state.device_class = None
        hass_state.friendly_name = None
        return hass_state


class TestHassConnectorErrorScenarios(TestCase):
    """Test comprehensive error handling scenarios"""
    
    def setUp(self):
        self.synchronizer = HassConnector()
    
    @patch.object(HassConnector, 'hass_manager')
    def test_sync_impl_handles_api_fetch_failure(self, mock_hass_manager):
        """Test sync helper handles API fetch failures"""
        # Mock manager with client that fails API fetch
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.include_filter = None
        mock_manager.fetch_hass_states_from_api.side_effect = Exception("API connection failed")
        mock_hass_manager.return_value = mock_manager
        
        with self.assertRaises(Exception) as context:
            self.synchronizer._sync_impl(is_initial_connect=True)
        
        self.assertEqual(str(context.exception), "API connection failed")
    
    @patch('hi.services.hass.hass_connector.HassConverter.hass_states_to_hass_devices')
    @patch.object(HassConnector, '_get_existing_hass_entities')
    @patch.object(HassConnector, 'hass_manager')
    def test_sync_impl_handles_converter_failure(
            self, mock_hass_manager, 
            mock_get_entities, mock_states_to_devices ):
        """Test sync helper handles converter failures"""
        # Setup mocks
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.include_filter = None
        mock_manager.fetch_hass_states_from_api.return_value = {'test': Mock()}
        mock_hass_manager.return_value = mock_manager
        
        mock_get_entities.return_value = {}
        
        # Mock converter failure
        mock_states_to_devices.side_effect = ValueError("Invalid state data format")
        
        with self.assertRaises(ValueError) as context:
            self.synchronizer._sync_impl(is_initial_connect=True)
        
        self.assertEqual(str(context.exception), "Invalid state data format")
    
    @patch('hi.services.hass.hass_connector.Entity.objects')
    def test_get_existing_entities_handles_database_error(self, mock_entity_objects):
        """Test _get_existing_hass_entities handles database errors"""
        # Mock database query failure
        mock_entity_objects.filter.side_effect = Exception("Database connection lost")
        
        result = IntegrationSyncResult(title='Test')
        
        with self.assertRaises(Exception) as context:
            self.synchronizer._get_existing_hass_entities(result)
        
        self.assertEqual(str(context.exception), "Database connection lost")


class TestHassConnectorMixinIntegration(TestCase):
    """Test integration with HassMixin"""

    def setUp(self):
        self.synchronizer = HassConnector()

    @patch('hi.services.hass.hass_mixins.HassManager')
    def test_hass_mixin_integration(self, mock_manager_class):
        """Test HassMixin integration provides hass_manager access"""
        mock_manager_instance = Mock()
        mock_manager_class.return_value = mock_manager_instance

        # Should be able to access hass_manager through mixin
        result = self.synchronizer.hass_manager()

        self.assertEqual(result, mock_manager_instance)


class TestHassConnectorSyncResultGrouping(TestCase):
    """Default-grouping behavior: entities are grouped by their
    ``EntityGroupType`` rollup label. Exercised here against
    HassGateway (which uses the framework default) — the same
    behavior applies to any integration that doesn't override
    group_entities_for_placement."""

    def setUp(self):
        self.synchronizer = HassGateway()

    def _entity(self, name, entity_type, integration_name):
        entity = Entity.objects.create(
            name=name,
            entity_type_str=str(entity_type),
            integration_id='hass',
            integration_name=integration_name,
        )
        return entity

    def test_groups_built_by_entity_group_alphabetical(self):
        """Group ordering is alphabetical by rollup label. LIGHT
        rolls up to AUTOMATION; MOTION_SENSOR to SECURITY."""
        from hi.apps.entity.enums import EntityType
        entities = [
            self._entity('Kitchen Light', EntityType.LIGHT, 'light.kitchen'),
            self._entity('Hall Sensor', EntityType.MOTION_SENSOR, 'binary_sensor.hall'),
            self._entity('Bedroom Light', EntityType.LIGHT, 'light.bedroom'),
        ]
        placement_input = self.synchronizer.group_entities_for_placement(entities)

        self.assertEqual(placement_input.ungrouped_items, [])
        self.assertEqual(
            [group.label for group in placement_input.groups],
            ['Automation', 'Security'],
        )
        self.assertEqual(
            [item.label for item in placement_input.groups[0].items],
            ['Kitchen Light', 'Bedroom Light'],
        )
        self.assertEqual(
            [item.label for item in placement_input.groups[1].items],
            ['Hall Sensor'],
        )

    def test_unrecognized_type_falls_back_to_general(self):
        """Entities with an unrecognized entity_type_str resolve to
        EntityType.OTHER, which rolls up to EntityGroupType.GENERAL."""
        entity = Entity.objects.create(
            name='Mystery',
            entity_type_str='UNRECOGNIZED_FUTURE_TYPE',
            integration_id='hass',
            integration_name='sensor.mystery',
        )
        placement_input = self.synchronizer.group_entities_for_placement([entity])

        self.assertEqual(placement_input.ungrouped_items, [])
        self.assertEqual(len(placement_input.groups), 1)
        self.assertEqual(placement_input.groups[0].label, 'General')
        self.assertEqual(placement_input.groups[0].items[0].entity, entity)

    def test_empty_input_yields_empty_groups(self):
        placement_input = self.synchronizer.group_entities_for_placement([])
        self.assertEqual(placement_input.groups, [])
        self.assertEqual(placement_input.ungrouped_items, [])
        self.assertTrue(placement_input.is_empty())

    def test_item_key_uses_integration_key(self):
        from hi.apps.entity.enums import EntityType
        entity = self._entity('Front Camera', EntityType.CAMERA, 'camera.front')
        placement_input = self.synchronizer.group_entities_for_placement([entity])
        self.assertEqual(placement_input.groups[0].items[0].key, 'hass:camera.front')


from hi.testing.async_task_utils import AsyncTaskTestCase


class TestHassConnectorCheckNeedsSync(AsyncTaskTestCase):
    """Issue #283 — sync-check probe shape for Home Assistant.

    Pins the contract that the upstream key set is *post-allowlist*
    (so the count matches what Refresh would actually import) and
    that the comparison is over aggregated HassDevice ids.

    Uses real Entity rows for the HI side so the probe's
    ``Entity.objects.filter(...)`` query path is exercised end-to-end.
    Only the upstream HTTP boundary
    (``fetch_hass_states_from_api_async``) is mocked.
    """

    def _hass_key(self, name: str):
        from hi.integrations.transient_models import IntegrationKey
        from hi.services.hass.hass_metadata import HassMetaData
        return IntegrationKey(
            integration_id=HassMetaData.integration_id,
            integration_name=name,
        )

    def _make_hass_entities(self, integration_names):
        from hi.services.hass.hass_metadata import HassMetaData
        for name in integration_names:
            Entity.objects.create(
                name=f'HASS Device {name}',
                entity_type_str='LIGHT',
                integration_id=HassMetaData.integration_id,
                integration_name=name,
            )

    def _run_check(self, hass_states_payload, allowlist=''):
        synchronizer = HassConnector()
        manager = Mock()
        manager.include_filter = allowlist

        async def fetch_states(verbose=True):
            return hass_states_payload

        manager.fetch_hass_states_from_api_async = fetch_states

        async def get_manager():
            return manager

        with patch.object(synchronizer, 'hass_manager_async', side_effect=get_manager):
            return self.run_async(synchronizer.check_needs_sync())

    def _hass_state(self, entity_id):
        """Build a minimal valid HassState via the converter helper."""
        from hi.services.hass.hass_converter import HassConverter
        return HassConverter.create_hass_state({
            'entity_id': entity_id,
            'state': 'on',
            'attributes': {},
            'last_changed': '2026-05-06T00:00:00+00:00',
            'last_updated': '2026-05-06T00:00:00+00:00',
            'last_reported': '2026-05-06T00:00:00+00:00',
            'context': {'id': '01', 'parent_id': None, 'user_id': None},
        })

    def test_in_sync_when_upstream_devices_match_hi(self):
        self._make_hass_entities(['kitchen', 'hall'])
        states = {
            'switch.kitchen': self._hass_state('switch.kitchen'),
            'switch.hall': self._hass_state('switch.hall'),
        }
        delta = self._run_check(
            hass_states_payload=states,
            allowlist='switch',
        )
        self.assertFalse(delta.needs_sync)

    def test_upstream_added_appears_in_delta(self):
        self._make_hass_entities(['kitchen', 'hall'])
        states = {
            'switch.kitchen': self._hass_state('switch.kitchen'),
            'switch.hall': self._hass_state('switch.hall'),
            'switch.garage': self._hass_state('switch.garage'),
        }
        delta = self._run_check(
            hass_states_payload=states,
            allowlist='switch',
        )
        self.assertEqual(delta.added, {self._hass_key('garage')})
        self.assertEqual(delta.removed, set())

    def test_upstream_removed_appears_in_delta(self):
        self._make_hass_entities(['kitchen', 'hall'])
        states = {
            'switch.kitchen': self._hass_state('switch.kitchen'),
        }
        delta = self._run_check(
            hass_states_payload=states,
            allowlist='switch',
        )
        self.assertEqual(delta.added, set())
        self.assertEqual(delta.removed, {self._hass_key('hall')})

    def test_allowlist_filters_upstream_set(self):
        # HA exposes a switch and a sensor; allowlist only allows
        # switch. The sensor should not appear in the upstream set,
        # so a HI side without 'weather' is still in sync.
        self._make_hass_entities(['kitchen'])
        states = {
            'switch.kitchen': self._hass_state('switch.kitchen'),
            'sensor.weather': self._hass_state('sensor.weather'),
        }
        delta = self._run_check(
            hass_states_payload=states,
            allowlist='switch',
        )
        self.assertFalse(delta.needs_sync)

    def test_returns_none_when_manager_not_ready(self):
        synchronizer = HassConnector()

        async def get_manager():
            return None

        with patch.object(synchronizer, 'hass_manager_async', side_effect=get_manager):
            result = self.run_async(synchronizer.check_needs_sync())

        self.assertIsNone(result)
