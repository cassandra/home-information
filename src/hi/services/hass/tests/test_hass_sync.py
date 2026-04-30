import json
import logging
import os
from unittest.mock import Mock, patch
from django.test import TestCase

from hi.apps.entity.models import Entity
from hi.integrations.sync_result import IntegrationSyncResult
from hi.integrations.transient_models import IntegrationKey

from hi.services.hass.hass_sync import HassSynchronizer
from hi.services.hass.hass_models import HassState

logging.disable(logging.CRITICAL)


class TestHassSynchronizerInitialization(TestCase):
    """Test HassSynchronizer initialization and basic setup"""
    
    def test_init_creates_instance_successfully(self):
        """Test HassSynchronizer initialization"""
        synchronizer = HassSynchronizer()
        self.assertIsInstance(synchronizer, HassSynchronizer)
    
    def test_synchronization_lock_name_constant(self):
        """All integration synchronizers share a single process-wide
        sync lock name; the base class declares it and subclasses do
        not override."""
        self.assertEqual(HassSynchronizer.SYNCHRONIZATION_LOCK_NAME, 'integrations_sync')
    
    def test_inherits_from_mixins(self):
        """Test that HassSynchronizer inherits from required mixins"""
        synchronizer = HassSynchronizer()

        # Should inherit from HassMixin
        self.assertTrue(hasattr(synchronizer, 'hass_manager'))


class TestHassSynchronizerSyncMethod(TestCase):
    """Test main sync() method with database transactions"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch('hi.integrations.integration_synchronizer.ExclusionLockContext')
    @patch.object(HassSynchronizer, '_sync_impl')
    def test_sync_handles_runtime_error(self, mock_sync_impl, mock_lock_context):
        """Test sync method handles RuntimeError exceptions"""
        # Mock RuntimeError in sync helper
        mock_sync_impl.side_effect = RuntimeError("Database connection failed")
        
        # Mock lock context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock()
        mock_context.__exit__ = Mock(return_value=False)
        mock_lock_context.return_value = mock_context
        
        result = self.synchronizer.sync()
        
        # Verify error handling
        self.assertIn('Database connection failed', result.error_list[0])
    
    @patch('hi.integrations.integration_synchronizer.ExclusionLockContext')
    @patch.object(HassSynchronizer, '_sync_impl')
    def test_sync_returns_error_result_on_exception(self, mock_sync_impl, mock_lock_context):
        """Test sync method returns proper error result when _sync_impl raises exception"""
        # Mock RuntimeError in sync helper
        mock_sync_impl.side_effect = RuntimeError("Database connection failed")
        
        # Mock lock context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock()
        mock_context.__exit__ = Mock(return_value=False)
        mock_lock_context.return_value = mock_context
        
        result = self.synchronizer.sync()
        
        # Verify actual error result structure and content
        self.assertEqual(len(result.error_list), 1)
        self.assertIn('Database connection failed', result.error_list[0])
        self.assertEqual(len(result.message_list), 0)  # No success messages on error


class TestHassSynchronizerSyncHelper(TestCase):
    """Test _sync_impl method logic"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
        
        # Mock hass_manager and dependencies
        self.mock_manager = Mock()
        self.mock_client = Mock()
        self.mock_manager.hass_client = self.mock_client
        self.mock_manager.import_allowlist = None


class TestHassSynchronizerStateConversion(TestCase):
    """Test HassSynchronizer with real HASS API data"""
    
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
        self.synchronizer = HassSynchronizer()
    
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


class TestHassSynchronizerTransactionBehavior(TestCase):
    """Test transaction handling and atomicity in sync operations"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    def test_sync_impl_executes_entity_operations_atomically(self):
        """Test that all entity operations in sync_helper execute within single transaction"""
        with patch.object(self.synchronizer, 'hass_manager') as mock_hass_manager, \
             patch.object(self.synchronizer, '_get_existing_hass_entities') as mock_get_entities, \
             patch.object(self.synchronizer, '_create_entity') as mock_create, \
             patch.object(self.synchronizer, '_remove_entity') as mock_remove:
            
            # Setup manager
            mock_manager = Mock()
            mock_manager.hass_client = Mock()
            mock_manager.import_allowlist = None
            mock_hass_manager.return_value = mock_manager

            # Setup scenario: one new device, one entity to remove
            api_states = {'light.new': self._create_mock_hass_state('light.new', 'light', 'on')}
            mock_manager.fetch_hass_states_from_api.return_value = api_states
            
            old_entity = Mock(spec=Entity)
            old_key = IntegrationKey(integration_id='hass', integration_name='old_device')
            mock_get_entities.return_value = {old_key: old_entity}
            
            # Track transaction usage
            with patch('hi.services.hass.hass_sync.transaction.atomic') as mock_atomic:
                mock_atomic.return_value.__enter__ = Mock()
                mock_atomic.return_value.__exit__ = Mock()
                
                result = self.synchronizer._sync_impl()
                
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
            mock_manager.import_allowlist = None
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
                    self.synchronizer._sync_impl()
                
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


class TestHassSynchronizerErrorScenarios(TestCase):
    """Test comprehensive error handling scenarios"""
    
    def setUp(self):
        self.synchronizer = HassSynchronizer()
    
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_sync_impl_handles_api_fetch_failure(self, mock_hass_manager):
        """Test sync helper handles API fetch failures"""
        # Mock manager with client that fails API fetch
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.import_allowlist = None
        mock_manager.fetch_hass_states_from_api.side_effect = Exception("API connection failed")
        mock_hass_manager.return_value = mock_manager
        
        with self.assertRaises(Exception) as context:
            self.synchronizer._sync_impl()
        
        self.assertEqual(str(context.exception), "API connection failed")
    
    @patch('hi.services.hass.hass_sync.HassConverter.hass_states_to_hass_devices')
    @patch.object(HassSynchronizer, '_get_existing_hass_entities')
    @patch.object(HassSynchronizer, 'hass_manager')
    def test_sync_impl_handles_converter_failure(
            self, mock_hass_manager, 
            mock_get_entities, mock_states_to_devices ):
        """Test sync helper handles converter failures"""
        # Setup mocks
        mock_manager = Mock()
        mock_manager.hass_client = Mock()
        mock_manager.import_allowlist = None
        mock_manager.fetch_hass_states_from_api.return_value = {'test': Mock()}
        mock_hass_manager.return_value = mock_manager
        
        mock_get_entities.return_value = {}
        
        # Mock converter failure
        mock_states_to_devices.side_effect = ValueError("Invalid state data format")
        
        with self.assertRaises(ValueError) as context:
            self.synchronizer._sync_impl()
        
        self.assertEqual(str(context.exception), "Invalid state data format")
    
    @patch('hi.services.hass.hass_sync.Entity.objects')
    def test_get_existing_entities_handles_database_error(self, mock_entity_objects):
        """Test _get_existing_hass_entities handles database errors"""
        # Mock database query failure
        mock_entity_objects.filter.side_effect = Exception("Database connection lost")
        
        result = IntegrationSyncResult(title='Test')
        
        with self.assertRaises(Exception) as context:
            self.synchronizer._get_existing_hass_entities(result)
        
        self.assertEqual(str(context.exception), "Database connection lost")


class TestHassSynchronizerMixinIntegration(TestCase):
    """Test integration with HassMixin"""

    def setUp(self):
        self.synchronizer = HassSynchronizer()

    @patch('hi.services.hass.hass_mixins.HassManager')
    def test_hass_mixin_integration(self, mock_manager_class):
        """Test HassMixin integration provides hass_manager access"""
        mock_manager_instance = Mock()
        mock_manager_class.return_value = mock_manager_instance

        # Should be able to access hass_manager through mixin
        result = self.synchronizer.hass_manager()

        self.assertEqual(result, mock_manager_instance)


class TestHassSynchronizerSyncResultGrouping(TestCase):
    """Phase 2 grouping behavior: HASS-imported entities are grouped
    by Hi-side entity_type_str. The /api/states endpoint exposes no
    area metadata, so the synchronizer falls back to entity_type as
    the meaningful, available signal."""

    def setUp(self):
        self.synchronizer = HassSynchronizer()

    def _entity(self, name, entity_type_str, integration_name):
        entity = Mock()
        entity.name = name
        entity.entity_type_str = entity_type_str
        entity.integration_key = IntegrationKey(
            integration_id='hass',
            integration_name=integration_name,
        )
        entity.id = 0
        return entity

    def test_groups_built_by_entity_type_alphabetical(self):
        """Group ordering is alphabetical for stable presentation."""
        entities = [
            self._entity('Kitchen Light', 'LIGHT', 'light.kitchen'),
            self._entity('Hall Sensor', 'SENSOR', 'binary_sensor.hall'),
            self._entity('Bedroom Light', 'LIGHT', 'light.bedroom'),
        ]
        groups = self.synchronizer._build_entity_type_groups(entities)

        self.assertEqual([group.label for group in groups], ['LIGHT', 'SENSOR'])
        self.assertEqual(
            [item.label for item in groups[0].items],
            ['Kitchen Light', 'Bedroom Light'],
        )
        self.assertEqual(
            [item.label for item in groups[1].items],
            ['Hall Sensor'],
        )

    def test_falls_back_to_other_when_entity_type_missing(self):
        """Entities missing entity_type_str land in an 'Other' bucket
        rather than dropping out of the result entirely."""
        entity = self._entity('Mystery', '', 'sensor.mystery')
        entity.entity_type_str = None
        groups = self.synchronizer._build_entity_type_groups([entity])

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].label, 'Other')
        self.assertEqual(groups[0].items[0].entity, entity)

    def test_empty_input_yields_empty_groups(self):
        self.assertEqual(self.synchronizer._build_entity_type_groups([]), [])

    def test_item_key_uses_integration_key(self):
        entity = self._entity('Front Camera', 'CAMERA', 'camera.front')
        groups = self.synchronizer._build_entity_type_groups([entity])
        self.assertEqual(groups[0].items[0].key, 'hass:camera.front')
