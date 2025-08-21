import logging
from unittest.mock import Mock, patch

from hi.apps.console.transient_view_manager import TransientViewManager
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestTransientViewManager(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Reset singleton state for each test
        TransientViewManager._instances = {}
        self.manager = TransientViewManager()

    def test_transient_view_manager_singleton_behavior(self):
        """Test TransientViewManager singleton pattern - critical for system consistency."""
        manager1 = TransientViewManager()
        manager2 = TransientViewManager()
        
        self.assertIs(manager1, manager2)
        return

    def test_priority_based_replacement_business_logic(self):
        """Test priority-based suggestion replacement - critical business logic for alert prioritization."""
        # Simulate realistic scenario: motion detection followed by critical alarm
        
        # Low priority motion detection from secondary camera
        self.manager.suggest_view_change(
            url='/console/sensor/backyard/video',
            duration_seconds=30,
            priority=10,  # Low priority
            trigger_reason='motion_detection_backyard'
        )
        
        initial_suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(initial_suggestion.url, '/console/sensor/backyard/video')
        
        # High priority motion detection from front door (security concern)
        self.manager.suggest_view_change(
            url='/console/sensor/frontdoor/video',
            duration_seconds=45,
            priority=100,  # High priority security event
            trigger_reason='motion_detection_entrance'
        )
        
        # Should replace with higher priority
        current_suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(current_suggestion.url, '/console/sensor/frontdoor/video')
        self.assertEqual(current_suggestion.priority, 100)
        
        # Lower priority subsequent event should be ignored
        self.manager.suggest_view_change(
            url='/console/sensor/garage/video',
            duration_seconds=30,
            priority=50,  # Medium priority, but lower than current
            trigger_reason='motion_detection_garage'
        )
        
        # Should still have high priority front door suggestion
        final_suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(final_suggestion.url, '/console/sensor/frontdoor/video')
        self.assertEqual(final_suggestion.priority, 100)
        return

    def test_equal_priority_replacement_for_newer_events(self):
        """Test equal priority replacement - ensures newer events of same importance are shown."""
        # Realistic scenario: Multiple motion events of same priority
        # User should see the most recent one
        
        self.manager.suggest_view_change(
            url='/console/sensor/zone1/video',
            duration_seconds=30,
            priority=50,
            trigger_reason='motion_zone1'
        )
        
        # Same priority event from different zone
        self.manager.suggest_view_change(
            url='/console/sensor/zone2/video',
            duration_seconds=30,
            priority=50,  # Same priority
            trigger_reason='motion_zone2'
        )
        
        # Should have the newer suggestion
        suggestion = self.manager.peek_current_suggestion()
        self.assertEqual(suggestion.url, '/console/sensor/zone2/video')
        self.assertEqual(suggestion.trigger_reason, 'motion_zone2')
        return

    def test_get_and_clear_pattern_for_api_consumption(self):
        """Test get_current_suggestion consumption pattern - critical for API endpoint behavior."""
        # This simulates how the API status endpoint consumes suggestions
        
        self.manager.suggest_view_change(
            url='/console/sensor/123/video',
            duration_seconds=30,
            priority=75,
            trigger_reason='motion_alarm'
        )
        
        # First API call gets the suggestion
        suggestion = self.manager.get_current_suggestion()
        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion.url, '/console/sensor/123/video')
        
        # Subsequent API calls should get None (suggestion consumed)
        next_suggestion = self.manager.get_current_suggestion()
        self.assertIsNone(next_suggestion)
        
        # This prevents the same suggestion from being sent multiple times
        self.assertFalse(self.manager.has_suggestion())
        return