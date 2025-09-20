"""
Tests for ZoneMinderManager class.

Focus on testing behavior and outcomes, not implementation details.
Uses real Django models and only mocks external HTTP calls.
"""

import threading
from unittest.mock import patch, Mock, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.test import TestCase, TransactionTestCase

from hi.apps.system.enums import HealthStatusType

from hi.integrations.models import Integration, IntegrationAttribute

from hi.services.zoneminder.zm_manager import ZoneMinderManager
from hi.services.zoneminder.enums import ZmAttributeType
from hi.services.zoneminder.zm_metadata import ZmMetaData


class ZoneMinderManagerSingletonTest(TestCase):
    """Test singleton behavior of ZoneMinderManager."""

    def test_singleton_returns_same_instance(self):
        """Multiple calls should return the same instance."""
        manager1 = ZoneMinderManager()
        manager2 = ZoneMinderManager()
        self.assertIs(manager1, manager2)

    def test_singleton_thread_safe(self):
        """Singleton should be thread-safe."""
        managers = []

        def create_manager():
            managers.append(ZoneMinderManager())

        # Create multiple threads trying to instantiate simultaneously
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_manager) for _ in range(10)]
            for future in as_completed(futures):
                future.result()  # Wait for completion

        # All should be the same instance
        first = managers[0]
        for manager in managers[1:]:
            self.assertIs(manager, first)


class ZoneMinderManagerConfigurationTest(TransactionTestCase):
    """Test configuration loading and validation behavior."""

    def setUp(self):
        """Create test integration and attributes."""
        self.integration = Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=True
        )

        # Create required attributes
        self.create_attribute(ZmAttributeType.API_URL, 'http://test.zm/api')
        self.create_attribute(ZmAttributeType.PORTAL_URL, 'http://test.zm')
        self.create_attribute(ZmAttributeType.API_USER, 'testuser')
        self.create_attribute(ZmAttributeType.API_PASSWORD, 'testpass')
        self.create_attribute(ZmAttributeType.TIMEZONE, 'America/Chicago')

    def tearDown(self):
        """Clean up singleton instance for next test."""
        # Reset singleton instance
        ZoneMinderManager._instance = None

    def create_attribute(self, attr_type, value):
        """Helper to create integration attributes."""
        return IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{str(attr_type)}",
            value=value,
            is_required=attr_type.is_required
        )

    @patch('hi.services.zoneminder.zm_client_factory.ZmClientFactory.create_client')
    def test_loads_configuration_on_first_access(self, mock_create_client):
        """Configuration should be loaded on first client access."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        manager = ZoneMinderManager()

        # Access client property - should trigger loading
        client = manager.zm_client

        # Verify client was created
        self.assertIsNotNone(client)
        mock_create_client.assert_called_once()

    def test_handles_missing_integration(self):
        """Should handle missing integration gracefully."""
        # Delete the integration
        self.integration.delete()

        manager = ZoneMinderManager()

        # Should not crash but client should be None
        client = manager.zm_client
        self.assertIsNone(client)

        # Health status should reflect the error
        health = manager.health_status
        self.assertFalse(health.is_healthy)

    def test_handles_disabled_integration(self):
        """Should handle disabled integration gracefully."""
        self.integration.is_enabled = False
        self.integration.save()

        manager = ZoneMinderManager()
        client = manager.zm_client

        self.assertIsNone(client)
        health = manager.health_status
        self.assertEqual(health.status, HealthStatusType.DISABLED)

    def test_validates_required_attributes(self):
        """Should validate that required attributes are present."""
        # Delete a required attribute
        IntegrationAttribute.objects.filter(
            integration_key_str__contains=str(ZmAttributeType.API_URL)
        ).delete()

        manager = ZoneMinderManager()
        client = manager.zm_client

        # Should handle missing required attribute
        self.assertIsNone(client)
        health = manager.health_status
        self.assertEqual(health.status, HealthStatusType.ERROR)


class ZoneMinderManagerThreadLocalTest(TransactionTestCase):
    """Test thread-local client behavior."""

    def setUp(self):
        """Create test integration and attributes."""
        self.integration = Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=True
        )

        # Create required attributes
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_URL}",
            value='http://test.zm/api',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.PORTAL_URL}",
            value='http://test.zm',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_USER}",
            value='testuser',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_PASSWORD}",
            value='testpass',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.TIMEZONE}",
            value='America/Chicago',
            is_required=True
        )

    def tearDown(self):
        """Clean up singleton instance for next test."""
        ZoneMinderManager._instance = None

    @patch('hi.services.zoneminder.zm_client_factory.ZmClientFactory.create_client')
    def test_each_thread_gets_own_client(self, mock_create_client):
        """Each thread should get its own client instance."""
        # Track which clients are created
        call_count = [0]  # Use list to modify in nested function

        def create_mock_client(*args, **kwargs):
            call_count[0] += 1
            # Create unique mock for each call
            mock = MagicMock()
            mock.id = call_count[0]  # Give each a unique ID
            return mock

        mock_create_client.side_effect = create_mock_client

        manager = ZoneMinderManager()
        results = {}
        event = threading.Event()

        def get_client(thread_name):
            client = manager.zm_client
            results[thread_name] = client
            event.set()

        # Get client from main thread
        main_client = manager.zm_client
        results['main'] = main_client

        # Get client from another thread
        thread = threading.Thread(target=get_client, args=('thread1',))
        thread.start()
        thread.join(timeout=1)

        # Each thread should have gotten a different client
        self.assertIsNotNone(results.get('main'))
        self.assertIsNotNone(results.get('thread1'))
        # Different mock objects should have different IDs
        self.assertNotEqual(results['main'].id, results['thread1'].id)
        # Should have created 2 clients
        self.assertEqual(call_count[0], 2)


class ZoneMinderManagerHealthStatusTest(TestCase):
    """Test health status tracking behavior."""

    def setUp(self):
        """Create test integration."""
        self.integration = Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=True
        )
        # Add minimal required attributes
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_URL}",
            value='http://test.zm/api',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.PORTAL_URL}",
            value='http://test.zm',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_USER}",
            value='testuser',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_PASSWORD}",
            value='testpass',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.TIMEZONE}",
            value='America/Chicago',
            is_required=True
        )

    def tearDown(self):
        """Clean up singleton instance."""
        ZoneMinderManager._instance = None

    def test_tracks_health_status(self):
        """Should track health status of integration."""
        manager = ZoneMinderManager()
        health = manager.health_status

        # Should have health status
        self.assertIsNotNone(health)
        self.assertIsNotNone(health.last_check)
        self.assertIsNotNone(health.status)


class ZoneMinderManagerReloadTest(TransactionTestCase):
    """Test configuration reload behavior."""

    def setUp(self):
        """Create test integration."""
        self.integration = Integration.objects.create(
            integration_id=ZmMetaData.integration_id,
            is_enabled=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_URL}",
            value='http://test.zm/api',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.PORTAL_URL}",
            value='http://test.zm',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_USER}",
            value='testuser',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.API_PASSWORD}",
            value='testpass',
            is_required=True
        )
        IntegrationAttribute.objects.create(
            integration=self.integration,
            integration_key_str=f"{ZmMetaData.integration_id}.{ZmAttributeType.TIMEZONE}",
            value='America/Chicago',
            is_required=True
        )

    def tearDown(self):
        """Clean up singleton instance."""
        ZoneMinderManager._instance = None

    @patch('hi.services.zoneminder.zm_client_factory.ZmClientFactory.create_client')
    def test_reload_clears_thread_local_clients(self, mock_create_client):
        """Reload should clear thread-local clients."""
        mock_create_client.return_value = Mock()

        manager = ZoneMinderManager()

        # Get a client to ensure one is created
        client1 = manager.zm_client
        self.assertIsNotNone(client1)

        # Reload configuration
        manager.reload()

        # Next access should create new client
        _ = manager.zm_client

        # Should have been called twice (initial + after reload)
        self.assertEqual(mock_create_client.call_count, 2)

    def test_notify_settings_changed_triggers_reload(self):
        """notify_settings_changed should trigger reload."""
        manager = ZoneMinderManager()

        # Register a callback to verify it gets called
        callback_called = []
        
        def test_callback():
            callback_called.append(True)

        manager.register_change_listener(test_callback)

        # Notify settings changed
        manager.notify_settings_changed()

        # Callback should have been called
        self.assertEqual(len(callback_called), 1)
        
