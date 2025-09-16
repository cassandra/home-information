import logging
import threading
from datetime import timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
import pytz

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.integrations.enums import IntegrationHealthStatusType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.transient_models import IntegrationKey
from hi.integrations.models import Integration, IntegrationAttribute

from hi.services.zoneminder.enums import ZmAttributeType
from hi.services.zoneminder.zm_manager import ZoneMinderManager
from hi.services.zoneminder.zm_metadata import ZmMetaData

logging.disable(logging.CRITICAL)


class TestZoneMinderManagerSingleton(TestCase):
    """Test singleton behavior and thread safety"""
    
    def setUp(self):
        # Reset singleton instance for each test
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
    
    def test_singleton_behavior(self):
        """Test that ZoneMinderManager follows singleton pattern"""
        manager1 = ZoneMinderManager()
        manager2 = ZoneMinderManager()
        self.assertIs(manager1, manager2)
        
    def test_singleton_thread_safety(self):
        """Test singleton creation is thread-safe"""
        results = []
        
        def create_manager():
            results.append(ZoneMinderManager())
        
        threads = [threading.Thread(target=create_manager) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
            
        # All instances should be the same object
        first_instance = results[0]
        for instance in results[1:]:
            self.assertIs(instance, first_instance)


class TestZoneMinderManagerInitialization(TestCase):
    """Test initialization and attribute loading"""
    
    def setUp(self):
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
        self.manager = ZoneMinderManager()
    
    def test_init_singleton_sets_defaults(self):
        """Test singleton initialization sets correct defaults"""
        self.assertEqual(self.manager._zm_attr_type_to_attribute, {})
        self.assertIsNone(self.manager._zm_client)
        self.assertEqual(self.manager._zm_state_list, [])
        self.assertEqual(self.manager._zm_monitor_list, [])
        self.assertEqual(self.manager._change_listeners, set())
        self.assertFalse(self.manager._was_initialized)
        self.assertIsNotNone(self.manager._data_lock)
    
    @patch('hi.services.zoneminder.zm_manager.ZoneMinderManager.reload')
    def test_ensure_initialized_calls_reload_once(self, mock_reload):
        """Test ensure_initialized only calls reload once"""
        self.manager.ensure_initialized()
        mock_reload.assert_called_once()
        
        # Second call should not trigger reload
        self.manager.ensure_initialized()
        mock_reload.assert_called_once()  # Still only one call
        
        self.assertTrue(self.manager._was_initialized)
    
    def test_reload_without_integration_in_database(self):
        """Test reload handles missing integration gracefully"""
        # Don't create any Integration in the database
        self.manager.reload()
        
        # Manager should still be functional, just with no configuration
        self.assertIsNotNone(self.manager)
        # Health status should reflect the configuration error
        health = self.manager.get_health_status()
        self.assertEqual(health.status, IntegrationHealthStatusType.CONFIG_ERROR)
        self.assertIn('not implemented', health.error_message)
    
    def test_reload_with_disabled_integration(self):
        """Test reload handles disabled integration gracefully"""
        # Create a disabled integration
        Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=False
        )
        
        self.manager.reload()
        
        # Health status should reflect the configuration error
        health = self.manager.get_health_status()
        self.assertEqual(health.status, IntegrationHealthStatusType.DISABLED)
    
    def test_reload_with_missing_required_attribute(self):
        """Test reload handles missing required attributes gracefully"""
        # Create an enabled integration but without required attributes
        Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=True
        )
        # Don't create any attributes - missing required ones
        
        self.manager.reload()
        
        # Health status should reflect the configuration error
        health = self.manager.get_health_status()
        self.assertEqual(health.status, IntegrationHealthStatusType.CONFIG_ERROR)
        self.assertIn('Missing ZM attribute', health.error_message)
    
    def test_reload_with_empty_required_value(self):
        """Test reload handles empty required attribute values gracefully"""
        # Create a real integration in the database
        integration = Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=True
        )
        
        # Create an attribute with whitespace-only value
        attr = IntegrationAttribute.objects.create(
            integration=integration,
            name=str(ZmAttributeType.API_URL),
            value='   ',  # Whitespace only
            is_required=True
        )
        attr.integration_key = IntegrationKey(
            integration_id=ZmMetaData.integration_id,
            integration_name=str(ZmAttributeType.API_URL)
        )
        attr.save()
        
        # Reload should handle this gracefully
        self.manager.reload()
        
        # Health status should reflect the configuration error
        health = self.manager.get_health_status()
        self.assertEqual(health.status, IntegrationHealthStatusType.CONFIG_ERROR)
        self.assertIn('Missing ZM attribute', health.error_message)
    
    def test_reload_success_with_all_required_attributes(self):
        """Test reload successfully configures manager with all required attributes"""
        # Create a real integration in the database
        integration = Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=True
        )
        
        # Create all required attributes with valid values
        for attr_type in ZmAttributeType:
            if attr_type.is_required:
                attr = IntegrationAttribute.objects.create(
                    integration=integration,
                    name=str(attr_type),
                    value=f'test_value_{attr_type.name}',
                    is_required=True
                )
                attr.integration_key = IntegrationKey(
                    integration_id=ZmMetaData.integration_id,
                    integration_name=str(attr_type)
                )
                attr.save()
        
        # Reload should configure the manager successfully
        self.manager.reload()
        
        # Health status should not have missing attribute errors
        health = self.manager.get_health_status()
        # Note: might still have connection errors if ZM API is unreachable,
        # but no missing attribute config errors
        self.assertNotIn('Missing ZM attribute', health.error_message)


class TestZoneMinderManagerClientCreation(TestCase):
    """Test ZM client creation and API option validation"""
    
    def setUp(self):
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
        self.manager = ZoneMinderManager()
    
    def create_mock_attributes(self):
        """Helper to create mock attributes for client creation"""
        attributes = {}
        attr_values = {
            ZmAttributeType.API_URL: 'https://test.com/zm/api',
            ZmAttributeType.PORTAL_URL: 'https://test.com/zm',
            ZmAttributeType.API_USER: 'testuser',
            ZmAttributeType.API_PASSWORD: 'testpass'
        }
        
        for attr_type, value in attr_values.items():
            mock_attr = Mock()
            mock_attr.value = value
            mock_attr.integration_key = IntegrationKey(
                integration_id=ZmMetaData.integration_id,
                integration_name=str(attr_type)
            )
            attributes[attr_type] = mock_attr
            
        return attributes
    
    def test_create_zm_client_missing_api_attribute(self):
        """Test create_zm_client raises error for missing API attributes"""
        incomplete_attributes = {
            ZmAttributeType.API_URL: Mock(value='https://test.com/api')
            # Missing other required API attributes
        }
        
        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager.create_zm_client(incomplete_attributes)
        
        self.assertIn('Missing ZM API attribute', str(context.exception))
    
    def test_create_zm_client_empty_api_attribute_value(self):
        """Test create_zm_client raises error for empty API attribute values"""
        attributes = self.create_mock_attributes()
        attributes[ZmAttributeType.API_URL].value = '   '  # Empty value
        
        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager.create_zm_client(attributes)
        
        self.assertIn('Missing ZM API attribute value for', str(context.exception))
    
    @patch('hi.services.zoneminder.zm_client_factory.ZMApi')
    def test_create_zm_client_success(self, mock_zmapi_class):
        """Test create_zm_client successfully delegates to factory"""
        # Arrange
        mock_client = Mock()
        mock_zmapi_class.return_value = mock_client
        attributes = self.create_mock_attributes()

        # For now, just test that the manager has a factory and delegates properly
        # The actual ZMApi creation with network calls is tested in the factory tests
        self.assertIsNotNone(self.manager._client_factory)
        self.assertTrue(hasattr(self.manager._client_factory, 'create_client'))

        # Act - Test that calling create_zm_client delegates to factory properly
        result = self.manager.create_zm_client(attributes)

        # Assert - Test delegation behavior without network calls
        self.assertIs(result, mock_client)
        mock_zmapi_class.assert_called_once()


class TestZoneMinderManagerCaching(TestCase):
    """Test TTL caching logic for states and monitors"""
    
    def setUp(self):
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
        self.manager = ZoneMinderManager()
        
        # Mock the zm_client
        self.mock_client = Mock()
        self.manager._zm_client = self.mock_client
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_zm_states_cache_miss_empty_list(self, mock_now):
        """Test get_zm_states fetches from API when list is empty and updates cache"""
        test_time = datetimeproxy.datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        mock_now.return_value = test_time
        
        # Create mock states with some identifiable data
        mock_state1 = Mock()
        mock_state1.get.return_value = {'State': {'Name': 'state1'}}
        mock_state2 = Mock()
        mock_state2.get.return_value = {'State': {'Name': 'state2'}}
        mock_states = [mock_state1, mock_state2]
        self.mock_client.states.return_value.list.return_value = mock_states
        
        # Verify initial cache state is empty
        self.assertEqual(self.manager._zm_state_list, [])
        self.assertEqual(self.manager._zm_state_timestamp, datetimeproxy.min())
        
        result = self.manager.get_zm_states()
        
        # Verify behavior: returns the correct states
        self.assertEqual(result, mock_states)
        self.assertEqual(len(result), 2)
        
        # Verify state changes: cache is populated and timestamp updated
        self.assertEqual(self.manager._zm_state_list, mock_states)
        self.assertEqual(self.manager._zm_state_timestamp, test_time)
        
        # Verify API was called (secondary to behavior verification)
        self.mock_client.states.assert_called_once()
        self.mock_client.states.return_value.list.assert_called_once()
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_zm_states_cache_hit_within_ttl(self, mock_now):
        """Test get_zm_states returns cached data within TTL without API call"""
        start_time = datetimeproxy.datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        mock_now.return_value = start_time
        
        # Set up cached data with identifiable content
        cached_state1 = Mock()
        cached_state1.get.return_value = {'State': {'Name': 'cached_state1'}}
        cached_state2 = Mock() 
        cached_state2.get.return_value = {'State': {'Name': 'cached_state2'}}
        cached_states = [cached_state1, cached_state2]
        self.manager._zm_state_list = cached_states
        self.manager._zm_state_timestamp = start_time
        
        # Advance time by less than TTL (300 seconds)
        mock_now.return_value = start_time + timedelta(seconds=200)
        
        result = self.manager.get_zm_states()
        
        # Verify behavior: returns exact cached data
        self.assertIs(result, cached_states)
        self.assertEqual(len(result), 2)
        
        # Verify state unchanged: cache timestamp and content remain the same
        self.assertEqual(self.manager._zm_state_timestamp, start_time)
        self.assertIs(self.manager._zm_state_list, cached_states)
        
        # Verify no API call was made (important for caching behavior)
        self.mock_client.states.assert_not_called()
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_zm_states_cache_miss_expired_ttl(self, mock_now):
        """Test get_zm_states fetches from API when TTL expired"""
        start_time = datetimeproxy.datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        
        # Set up cached data
        cached_states = [Mock(), Mock()]
        self.manager._zm_state_list = cached_states
        self.manager._zm_state_timestamp = start_time
        
        # Advance time beyond TTL (300 seconds)
        mock_now.return_value = start_time + timedelta(seconds=400)
        
        new_states = [Mock(), Mock(), Mock()]
        self.mock_client.states.return_value.list.return_value = new_states
        
        result = self.manager.get_zm_states()
        
        self.mock_client.states.assert_called_once()
        self.assertEqual(result, new_states)
        self.assertEqual(self.manager._zm_state_list, new_states)
    
    def test_get_zm_states_force_load_bypasses_cache(self):
        """Test get_zm_states with force_load=True bypasses cache"""
        # Set up cached data
        cached_states = [Mock(), Mock()]
        self.manager._zm_state_list = cached_states
        self.manager._zm_state_timestamp = datetimeproxy.now()
        
        new_states = [Mock(), Mock(), Mock()]
        self.mock_client.states.return_value.list.return_value = new_states
        
        result = self.manager.get_zm_states(force_load=True)
        
        self.mock_client.states.assert_called_once()
        self.assertEqual(result, new_states)
    
    @patch('hi.apps.common.datetimeproxy.now')
    def test_get_zm_monitors_cache_behavior(self, mock_now):
        """Test get_zm_monitors follows same caching pattern as states"""
        test_time = datetimeproxy.datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
        mock_now.return_value = test_time
        
        mock_monitors = [Mock(), Mock()]
        self.mock_client.monitors.return_value.list.return_value = mock_monitors
        
        result = self.manager.get_zm_monitors()
        
        # Verify force_reload option is passed to pyzm
        expected_options = {'force_reload': True}
        self.mock_client.monitors.assert_called_once_with(expected_options)
        self.assertEqual(result, mock_monitors)
    
    def test_clear_caches_resets_cached_data(self):
        """Test clear_caches resets both state and monitor caches"""
        # Set up cached data
        self.manager._zm_state_list = [Mock(), Mock()]
        self.manager._zm_monitor_list = [Mock(), Mock(), Mock()]
        
        self.manager.clear_caches()
        
        self.assertEqual(self.manager._zm_state_list, [])
        self.assertEqual(self.manager._zm_monitor_list, [])


class TestZoneMinderManagerTimezoneValidation(TestCase):
    """Test complex timezone validation business logic"""
    
    def setUp(self):
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
        self.manager = ZoneMinderManager()
    
    @patch.object(Integration.objects, 'get')
    @patch.object(IntegrationAttribute.objects, 'filter')
    @patch('hi.apps.common.datetimeproxy.is_valid_timezone_name')
    def test_get_zm_tzname_valid_timezone(self, mock_is_valid, mock_filter, mock_get):
        """Test get_zm_tzname returns valid timezone"""
        mock_integration = Mock()
        mock_get.return_value = mock_integration
        
        mock_attr = Mock()
        mock_attr.value = 'America/Chicago'
        mock_filter.return_value.first.return_value = mock_attr
        
        mock_is_valid.return_value = True
        
        result = self.manager.get_zm_tzname()
        
        self.assertEqual(result, 'America/Chicago')
        mock_is_valid.assert_called_once_with(tz_name='America/Chicago')
    
    @patch.object(Integration.objects, 'get')
    @patch.object(IntegrationAttribute.objects, 'filter')
    @patch('hi.apps.common.datetimeproxy.is_valid_timezone_name')
    def test_get_zm_tzname_invalid_timezone_fallback(self, mock_is_valid, mock_filter, mock_get):
        """Test get_zm_tzname falls back to UTC for invalid timezone"""
        mock_integration = Mock()
        mock_get.return_value = mock_integration
        
        mock_attr = Mock()
        mock_attr.value = 'Invalid/Timezone'
        mock_filter.return_value.first.return_value = mock_attr
        
        mock_is_valid.return_value = False
        
        result = self.manager.get_zm_tzname()
        
        self.assertEqual(result, 'UTC')
    
    @patch.object(Integration.objects, 'get')
    @patch.object(IntegrationAttribute.objects, 'filter')
    def test_get_zm_tzname_no_attribute_fallback(self, mock_filter, mock_get):
        """Test get_zm_tzname falls back to UTC when no attribute found"""
        mock_integration = Mock()
        mock_get.return_value = mock_integration
        
        mock_filter.return_value.first.return_value = None
        
        result = self.manager.get_zm_tzname()
        
        self.assertEqual(result, 'UTC')
    
    @patch.object(Integration.objects, 'get')
    def test_get_zm_tzname_integration_not_found_fallback(self, mock_get):
        """Test get_zm_tzname falls back to UTC when integration not found"""
        mock_get.side_effect = Integration.DoesNotExist
        
        result = self.manager.get_zm_tzname()
        
        self.assertEqual(result, 'UTC')
    
    @patch.object(Integration.objects, 'get')
    @patch.object(IntegrationAttribute.objects, 'filter')
    def test_get_zm_tzname_integration_attribute_not_found_fallback(self, mock_filter, mock_get):
        """Test get_zm_tzname falls back to UTC when integration attribute not found"""
        mock_integration = Mock()
        mock_get.return_value = mock_integration
        
        # Simulate IntegrationAttribute.DoesNotExist by making filter().first() raise it
        mock_filter.return_value.first.side_effect = IntegrationAttribute.DoesNotExist
        
        result = self.manager.get_zm_tzname()
        
        self.assertEqual(result, 'UTC')


class TestZoneMinderManagerChangeListeners(TestCase):
    """Test change listener callback system and thread safety"""
    
    def setUp(self):
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
        self.manager = ZoneMinderManager()
    
    def test_register_change_listener(self):
        """Test registering change listeners"""
        callback1 = Mock()
        callback2 = Mock()
        
        self.manager.register_change_listener(callback1)
        self.manager.register_change_listener(callback2)
        
        self.assertEqual(len(self.manager._change_listeners), 2)
        self.assertIn(callback1, self.manager._change_listeners)
        self.assertIn(callback2, self.manager._change_listeners)

    def test_register_change_listener_prevents_duplicates(self):
        """Test that registering the same listener multiple times only adds it once"""
        callback = Mock()

        # Register the same callback multiple times
        self.manager.register_change_listener(callback)
        self.manager.register_change_listener(callback)
        self.manager.register_change_listener(callback)

        # Should only be registered once
        self.assertEqual(len(self.manager._change_listeners), 1)
        self.assertIn(callback, self.manager._change_listeners)

        # Verify it's only called once when settings change
        self.manager.notify_settings_changed()
        callback.assert_called_once()
    
    @patch.object(ZoneMinderManager, 'reload')
    def test_notify_settings_changed_calls_reload_and_listeners(self, mock_reload):
        """Test notify_settings_changed triggers reload and notifies all registered listeners"""
        # Create trackable callback functions
        callback1_called = []
        callback2_called = []
        
        def callback1():
            callback1_called.append(True)
        
        def callback2():
            callback2_called.append(True)
            
        # Verify initial state: no listeners registered
        self.assertEqual(len(self.manager._change_listeners), 0)
        
        # Register listeners and verify they are stored
        self.manager.register_change_listener(callback1)
        self.manager.register_change_listener(callback2)
        self.assertEqual(len(self.manager._change_listeners), 2)
        
        # Verify initial callback state
        self.assertEqual(len(callback1_called), 0)
        self.assertEqual(len(callback2_called), 0)
        
        self.manager.notify_settings_changed()
        
        # Verify behavior: reload was triggered
        mock_reload.assert_called_once()
        
        # Verify behavior: all callbacks were executed
        self.assertEqual(len(callback1_called), 1)
        self.assertEqual(len(callback2_called), 1)
        
        # Verify state: listeners remain registered for future notifications
        self.assertEqual(len(self.manager._change_listeners), 2)
    
    @patch.object(ZoneMinderManager, 'reload')
    def test_notify_settings_changed_handles_callback_exceptions(self, mock_reload):
        """Test notify_settings_changed continues if callback raises exception"""
        callback1 = Mock()
        callback2 = Mock(side_effect=Exception("Test exception"))
        callback3 = Mock()
        
        self.manager.register_change_listener(callback1)
        self.manager.register_change_listener(callback2)
        self.manager.register_change_listener(callback3)
        
        # Should not raise exception despite callback2 failing
        self.manager.notify_settings_changed()
        
        # All callbacks should be attempted
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()


class TestZoneMinderManagerUrlGeneration(TestCase):
    """Test URL generation for video streams"""
    
    def setUp(self):
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
        self.manager = ZoneMinderManager()
        
        # Mock client with portal URL
        self.mock_client = Mock()
        self.mock_client.portal_url = 'https://test.com/zm'
        self.manager._zm_client = self.mock_client
    
    def test_get_video_stream_url(self):
        """Test video stream URL generation"""
        monitor_id = 123
        expected_url = 'https://test.com/zm/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=5&maxfps=5&monitor=123'
        
        result = self.manager.get_video_stream_url(monitor_id)
        
        self.assertEqual(result, expected_url)
    
    def test_get_event_video_stream_url(self):
        """Test event video stream URL generation"""
        event_id = 456
        expected_base_url = (
            'https://test.com/zm/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=5&'
            'maxfps=5&replay=single&source=event&event=456&_t='
        )
        
        result = self.manager.get_event_video_stream_url(event_id)
        
        # Check that URL starts with expected base and includes timestamp
        self.assertTrue(result.startswith(expected_base_url))
        
        # Extract and validate timestamp parameter
        timestamp_part = result[len(expected_base_url):]
        self.assertTrue(timestamp_part.isdigit())
        self.assertGreater(int(timestamp_part), 0)


class TestZoneMinderManagerBooleanConversion(TestCase):
    """Test enum property conversion with custom logic"""
    
    def setUp(self):
        ZoneMinderManager._instance = None
        ZoneMinderManager._lock = threading.Lock()
        self.manager = ZoneMinderManager()
    
    @patch('hi.services.zoneminder.zm_manager.str_to_bool')
    def test_should_add_alarm_events_true(self, mock_str_to_bool):
        """Test should_add_alarm_events returns True when attribute is true"""
        mock_attribute = Mock()
        mock_attribute.value = 'true'
        self.manager._zm_attr_type_to_attribute = {
            ZmAttributeType.ADD_ALARM_EVENTS: mock_attribute
        }
        
        mock_str_to_bool.return_value = True
        
        result = self.manager.should_add_alarm_events
        
        self.assertTrue(result)
        mock_str_to_bool.assert_called_once_with('true')
    
    def test_should_add_alarm_events_false_when_no_attribute(self):
        """Test should_add_alarm_events returns False when no attribute"""
        self.manager._zm_attr_type_to_attribute = {}
        
        result = self.manager.should_add_alarm_events
        
        self.assertFalse(result)
