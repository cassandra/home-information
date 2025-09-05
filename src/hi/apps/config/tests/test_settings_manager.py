import logging
from threading import Lock
import threading

from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.config.settings_manager import SettingsManager
from hi.apps.config.setting_enums import SettingEnum, SettingDefinition
from hi.apps.attribute.enums import AttributeValueType
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSetting(SettingEnum):
    TEST_SETTING = SettingDefinition(
        label='Test Setting',
        description='A test setting',
        value_type=AttributeValueType.TEXT,
        value_range_str='',
        is_editable=True,
        is_required=True,
        initial_value='test_initial',
    )


class TestSettingsManager(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Reset SettingsManager singleton for proper test isolation
        SettingsManager._instance = None

    def test_singleton_behavior(self):
        """Test SettingsManager singleton pattern - critical for system consistency."""
        manager1 = SettingsManager()
        manager2 = SettingsManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_initialization_lifecycle(self):
        """Test complete initialization lifecycle."""
        manager = SettingsManager()
        
        # Ensure manager is initialized (it may already be from other tests)
        manager.ensure_initialized()
        self.assertTrue(manager._was_initialized)
        
        # Subsystems should be loaded
        subsystems = manager.get_subsystems()
        self.assertIsInstance(subsystems, list)
        return

    def test_setting_value_management_workflow(self):
        """Test complete workflow of setting value management."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Create test subsystem and attribute
        subsystem = Subsystem.objects.create(
            name='Test Subsystem',
            subsystem_key='test_workflow',
        )
        test_key = TestSetting.TEST_SETTING.key
        attribute = SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key=test_key,
            value_type=AttributeValueType.TEXT,
            value='initial_workflow_value',
        )
        
        # Reload subsystems and attributes to pick up new data
        manager._subsystem_list = manager._load_settings()
        manager.reload()
        
        # Test getting setting value
        initial_value = manager.get_setting_value(TestSetting.TEST_SETTING)
        self.assertEqual(initial_value, 'initial_workflow_value')
        
        # Test updating setting value
        manager.set_setting_value(TestSetting.TEST_SETTING, 'updated_workflow_value')
        
        # Verify update was applied
        updated_value = manager.get_setting_value(TestSetting.TEST_SETTING)
        self.assertEqual(updated_value, 'updated_workflow_value')
        
        # Verify database persistence
        attribute.refresh_from_db()
        self.assertEqual(attribute.value, 'updated_workflow_value')
        return

    def test_setting_value_error_scenarios(self):
        """Test error handling in setting value operations."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Test KeyError for non-existent setting
        with self.assertRaises(KeyError):
            manager.set_setting_value(TestSetting.TEST_SETTING, 'any_value')
        
        # Test None return for non-existent setting
        value = manager.get_setting_value(TestSetting.TEST_SETTING)
        self.assertIsNone(value)
        return

    def test_change_listener_notification_system(self):
        """Test change listener system with real callbacks."""
        manager = SettingsManager()
        
        # Track notifications with simple state
        notification_count = [0]  # Use list for mutable reference
        listener_called = [False]
        
        def test_callback():
            notification_count[0] += 1
            listener_called[0] = True
        
        manager.register_change_listener(test_callback)
        
        # Create test data to trigger reload
        Subsystem.objects.create(
            name='Listener Test Subsystem',
            subsystem_key='listener_test',
        )
        
        # Initialize and reload to trigger notifications
        manager.ensure_initialized()
        initial_count = notification_count[0]
        
        manager.reload()
        
        # Verify callback was invoked
        self.assertTrue(listener_called[0])
        self.assertGreater(notification_count[0], initial_count)
        return

    def test_change_listener_resilience(self):
        """Test system resilience when change listeners fail."""
        manager = SettingsManager()
        
        # Track successful callback execution
        successful_callback_executed = [False]
        
        def failing_callback():
            raise ValueError("Simulated callback failure")
        
        def successful_callback():
            successful_callback_executed[0] = True
        
        # Register both callbacks
        manager.register_change_listener(failing_callback)
        manager.register_change_listener(successful_callback)
        
        # Create test data
        Subsystem.objects.create(
            name='Resilience Test Subsystem',
            subsystem_key='resilience_test',
        )
        
        # Reload should not fail despite exception in first callback
        manager.ensure_initialized()
        successful_callback_executed[0] = False  # Reset flag
        manager.reload()
        
        # Successful callback should still execute
        self.assertTrue(successful_callback_executed[0])
        return

    def test_database_synchronization(self):
        """Test manager stays synchronized with database changes."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Create initial test data
        subsystem = Subsystem.objects.create(
            name='Sync Test Subsystem',
            subsystem_key='sync_test',
        )
        test_key = 'test.sync.setting'
        attribute = SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key=test_key,
            value_type=AttributeValueType.TEXT,
            value='sync_initial_value',
        )
        
        # Reload subsystems and attributes to pick up new data
        manager._subsystem_list = manager._load_settings()
        manager.reload()
        
        # Verify initial state
        initial_value = manager.get_setting_value(
            type('MockSetting', (), {'key': test_key})()
        )
        self.assertEqual(initial_value, 'sync_initial_value')
        
        # Modify database directly
        attribute.value = 'sync_modified_value'
        attribute.save()
        
        # Reload should pick up changes
        manager.reload()
        updated_value = manager.get_setting_value(
            type('MockSetting', (), {'key': test_key})()
        )
        self.assertEqual(updated_value, 'sync_modified_value')
        return

    def test_subsystem_management(self):
        """Test subsystem management functionality."""
        manager = SettingsManager()
        manager.ensure_initialized()
        
        # Create test subsystems
        Subsystem.objects.create(
            name='Management Test 1',
            subsystem_key='mgmt_test_1',
        )
        Subsystem.objects.create(
            name='Management Test 2',
            subsystem_key='mgmt_test_2',
        )
        
        # Reload subsystems to pick up new subsystems
        manager._subsystem_list = manager._load_settings()
        manager.reload()
        
        # Test subsystem retrieval - just verify the new ones are present
        updated_subsystems = manager.get_subsystems()
        subsystem_keys = [s.subsystem_key for s in updated_subsystems]
        
        self.assertIn('mgmt_test_1', subsystem_keys)
        self.assertIn('mgmt_test_2', subsystem_keys)
        
        # Verify subsystems can be retrieved individually
        mgmt_subsystems = [s for s in updated_subsystems if s.subsystem_key.startswith('mgmt_test_')]
        self.assertEqual(len(mgmt_subsystems), 2)
        return

    def test_server_startup_tracking(self):
        """Test server startup datetime tracking."""
        manager = SettingsManager()
        
        startup_time = manager.get_server_start_datetime()
        self.assertIsNotNone(startup_time)
        
        # Should be consistent across calls
        startup_time2 = manager.get_server_start_datetime()
        self.assertEqual(startup_time, startup_time2)
        return

    def test_thread_safety_infrastructure(self):
        """Test thread safety infrastructure is properly configured."""
        manager = SettingsManager()
        
        # Verify locks exist and are proper lock types  
        lock_types = (type(Lock()), type(threading.Lock()), type(threading.RLock()))
        self.assertIsInstance(manager._subsystems_lock, lock_types)
        self.assertIsInstance(manager._attributes_lock, lock_types)
        
        # Test that locks can be acquired and released
        with manager._subsystems_lock:
            self.assertTrue(True)  # Lock acquisition succeeded
        
        with manager._attributes_lock:
            self.assertTrue(True)  # Lock acquisition succeeded
        return
