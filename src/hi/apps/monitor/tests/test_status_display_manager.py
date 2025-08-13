import logging
import threading
from unittest.mock import patch

from hi.apps.monitor.status_display_manager import StatusDisplayManager
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestStatusDisplayManager(BaseTestCase):

    def test_status_display_manager_singleton_behavior(self):
        """Test StatusDisplayManager singleton pattern - critical for system consistency."""
        manager1 = StatusDisplayManager()
        manager2 = StatusDisplayManager()
        
        # Should be the same instance
        self.assertIs(manager1, manager2)
        return

    def test_status_display_manager_ttl_cache_initialization(self):
        """Test TTL cache initialization - critical for performance optimization."""
        manager = StatusDisplayManager()
        
        # Should have initialized TTL cache for status value overrides
        self.assertIsNotNone(manager._status_value_overrides)
        
        # Cache should have reasonable TTL
        self.assertEqual(manager.STATUS_VALUE_OVERRIDES_SECS, 11)
        self.assertGreater(manager.STATUS_VALUE_OVERRIDES_SECS, 0)
        self.assertLess(manager.STATUS_VALUE_OVERRIDES_SECS, 60)
        return

    def test_status_display_manager_cache_maxsize(self):
        """Test TTL cache size limits - important for memory management."""
        manager = StatusDisplayManager()
        
        # Cache should have reasonable size limit
        cache = manager._status_value_overrides
        self.assertEqual(cache.maxsize, 100)
        self.assertGreater(cache.maxsize, 0)
        self.assertLess(cache.maxsize, 1000)
        return

    def test_status_display_manager_cache_ttl_behavior(self):
        """Test TTL cache expiration behavior - critical for data freshness."""
        manager = StatusDisplayManager()
        cache = manager._status_value_overrides
        
        # Test that cache accepts and stores values
        test_key = 'test_entity_123'
        test_value = 'override_value'
        
        cache[test_key] = test_value
        
        # Should retrieve stored value
        self.assertEqual(cache[test_key], test_value)
        self.assertIn(test_key, cache)
        
        # Should have proper TTL (we can't easily test expiration in unit tests)
        self.assertEqual(cache.ttl, manager.STATUS_VALUE_OVERRIDES_SECS)
        return

    def test_status_display_manager_mixin_inheritance(self):
        """Test SensorResponseMixin inheritance - critical for sensor integration."""
        manager = StatusDisplayManager()
        
        # Should inherit from SensorResponseMixin
        from hi.apps.sense.sensor_response_manager import SensorResponseMixin
        self.assertIsInstance(manager, SensorResponseMixin)
        return

    @patch('hi.apps.monitor.status_display_manager.StatusDisplayManager.get_all_entity_state_status_data_list')
    def test_status_display_manager_get_status_css_class_update_map(self, mock_get_data):
        """Test CSS class update map generation - critical for UI updates."""
        # Mock the complex data retrieval method
        mock_get_data.return_value = []
        
        manager = StatusDisplayManager()
        
        # Should return a dictionary for CSS class updates
        update_map = manager.get_status_css_class_update_map()
        self.assertIsInstance(update_map, dict)
        
        # Should call the data retrieval method
        mock_get_data.assert_called_once()
        return

    def test_status_display_manager_thread_safety_cache_access(self):
        """Test thread-safe cache access - critical for concurrent operations."""
        manager = StatusDisplayManager()
        cache = manager._status_value_overrides
        
        results = []
        errors = []
        
        def cache_operation(thread_id):
            try:
                # Perform cache operations that might conflict
                key = f'test_key_{thread_id}'
                value = f'test_value_{thread_id}'
                
                cache[key] = value
                retrieved = cache.get(key)
                results.append((thread_id, retrieved == value))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads to test concurrent access
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should not have any errors and all operations should succeed
        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        self.assertEqual(len(results), 5)
        
        for thread_id, success in results:
            self.assertTrue(success, f"Thread {thread_id} cache operation failed")
        return
