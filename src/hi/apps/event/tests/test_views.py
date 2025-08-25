import logging

from django.urls import reverse

from hi.apps.config.enums import ConfigPageType
from hi.apps.event.models import EventDefinition, EventHistory
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestEventDefinitionsView(SyncViewTestCase):
    """
    Tests for EventDefinitionsView - demonstrates ConfigPageView testing.
    This view displays the event definitions configuration page.
    """

    def setUp(self):
        super().setUp()
        # Create test event definitions
        self.event_definition1 = EventDefinition.objects.create(
            name='Test Event 1',
            event_type_str='TEST',
            event_window_secs=60,
            dedupe_window_secs=300
        )
        self.event_definition2 = EventDefinition.objects.create(
            name='Test Event 2',
            event_type_str='TEST',
            event_window_secs=120,
            dedupe_window_secs=600
        )

    def test_get_event_definitions_page(self):
        """Test getting event definitions configuration page."""
        url = reverse('event_definitions')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/panes/event_definitions.html')

    def test_event_definitions_in_context(self):
        """Test that event definitions are passed to template context."""
        url = reverse('event_definitions')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        event_list = response.context['event_definition_list']
        self.assertEqual(len(event_list), 2)
        
        # Should be ordered by name
        self.assertEqual(event_list[0].name, 'Test Event 1')
        self.assertEqual(event_list[1].name, 'Test Event 2')

    def test_config_page_type_is_events(self):
        """Test that the config page type is set correctly."""
        from hi.apps.event.views import EventDefinitionsView
        view = EventDefinitionsView()
        self.assertEqual(view.config_page_type, ConfigPageType.EVENTS)

    def test_prefetch_related_optimizations(self):
        """Test that related objects are prefetched for performance."""
        url = reverse('event_definitions')
        
        # Monitor database queries to ensure prefetch is working
        # Prefetch_related executes multiple queries efficiently:
        # 1 for main objects + 1 for each relationship = ~4 queries total
        # Plus some additional queries for session/collections = ~6-10 total
        response = self.client.get(url)
        event_list = response.context['event_definition_list']
        
        # The key test: accessing related fields should NOT trigger additional queries
        # because they were prefetched
        with self.assertNumQueries(0):  # No additional queries should be needed
            for event in event_list:
                _ = list(event.event_clauses.all())
                _ = list(event.alarm_actions.all())
                _ = list(event.control_actions.all())

    def test_empty_event_definitions_list(self):
        """Test page displays correctly when no event definitions exist."""
        # Delete all event definitions
        EventDefinition.objects.all().delete()
        
        url = reverse('event_definitions')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        event_list = response.context['event_definition_list']
        self.assertEqual(len(event_list), 0)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('event_definitions')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestEventHistoryView(DualModeViewTestCase):
    """
    Tests for EventHistoryView - demonstrates HiModalView with pagination testing.
    This view displays the history of event occurrences.
    """

    def setUp(self):
        super().setUp()
        # Create test event definition
        self.event_definition = EventDefinition.objects.create(
            name='Test Event',
            event_type_str='TEST',
            event_window_secs=60,
            dedupe_window_secs=300
        )
        
        # Create test event history entries
        for i in range(5):
            EventHistory.objects.create(
                event_definition=self.event_definition,
                event_datetime=f'2023-01-0{i+1}T12:00:00Z'
            )

    def test_get_event_history_sync(self):
        """Test getting event history with synchronous request."""
        url = reverse('event_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'event/modals/event_history.html')

    def test_get_event_history_async(self):
        """Test getting event history with AJAX request."""
        url = reverse('event_history')
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # HiModalView returns JSON with modal content for AJAX requests
        data = response.json()
        self.assertIn('modal', data)

    def test_event_history_and_pagination_in_context(self):
        """Test that event history and pagination are passed to template context."""
        url = reverse('event_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertIn('grouped_events', response.context)
        self.assertIn('pagination', response.context)
        
        # Should have our test entries grouped by date
        grouped_events = response.context['grouped_events']
        total_events = sum(len(group['events']) for group in grouped_events)
        self.assertEqual(total_events, 5)

    def test_pagination_configuration(self):
        """Test that pagination is properly configured."""
        url = reverse('event_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        pagination = response.context['pagination']
        self.assertIsNotNone(pagination)
        # Should have base URL for event history
        self.assertIn('/event/history', pagination.base_url)

    def test_pagination_with_many_entries(self):
        """Test pagination when there are many event history entries."""
        # Create many more history entries to test pagination
        for i in range(50):
            EventHistory.objects.create(
                event_definition=self.event_definition,
                event_datetime=f'2023-02-{(i % 28) + 1:02d}T12:00:00Z'
            )

        url = reverse('event_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        grouped_events = response.context['grouped_events']
        total_events = sum(len(group['events']) for group in grouped_events)
        
        # Should be limited by page size (25)
        self.assertLessEqual(total_events, 25)

    def test_pagination_page_size_constant(self):
        """Test that the page size constant is used correctly."""
        from hi.apps.event.views import EventHistoryView
        self.assertEqual(EventHistoryView.EVENT_HISTORY_PAGE_SIZE, 25)

    def test_empty_event_history_list(self):
        """Test page displays correctly when no event history exists."""
        # Delete all event history
        EventHistory.objects.all().delete()
        
        url = reverse('event_history')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        grouped_events = response.context['grouped_events']
        self.assertEqual(len(grouped_events), 0)

    def test_pagination_with_page_parameter(self):
        """Test pagination with specific page parameter."""
        # Create enough entries to have multiple pages
        for i in range(30):
            EventHistory.objects.create(
                event_definition=self.event_definition,
                event_datetime=f'2023-03-{(i % 28) + 1:02d}T12:00:00Z'
            )

        url = reverse('event_history')
        response = self.client.get(url, {'page': '2'})

        self.assertSuccessResponse(response)
        # Should still return valid response for page 2
        self.assertIn('grouped_events', response.context)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('event_history')
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)
        
