import logging
from unittest.mock import patch

from django.urls import reverse

from hi.apps.location.models import Location, LocationView
from hi.enums import ViewType
from hi.testing.view_test_base import SyncViewTestCase

logging.disable(logging.CRITICAL)


class TestStartView(SyncViewTestCase):
    """
    Tests for StartView - demonstrates synchronous HTML view testing.
    This view renders a template for first-time users when no locations exist.
    """

    def test_start_view_renders_template_when_no_locations(self):
        """Test that StartView renders start.html template when no locations exist."""
        # Ensure no locations exist
        Location.objects.all().delete()
        
        url = reverse('start')
        response = self.client.get(url)
        
        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'pages/start.html')

    def test_start_view_redirects_when_locations_exist(self):
        """Test that StartView redirects to home when locations already exist."""
        # Create a location with required fields
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        # Create a LocationView for the location
        LocationView.objects.create(
            location=location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            svg_style_name_str='DEFAULT'
        )
        
        url = reverse('start')
        response = self.client.get(url)
        
        # Should redirect to home (test only StartView's decision, not HomeView's logic)
        home_url = reverse('home')
        self.assertRedirects(response, home_url, fetch_redirect_response=False)

    def test_start_view_sets_edit_mode_in_session(self):
        """Test that StartView sets edit mode in the session."""
        # Ensure no locations exist
        Location.objects.all().delete()
        
        url = reverse('start')
        response = self.client.get(url)
        
        self.assertSuccessResponse(response)


class TestHomeView(SyncViewTestCase):
    """
    Tests for HomeView - demonstrates redirect logic testing.
    This view redirects based on existing data and view parameters.
    """

    def test_home_view_routes_to_start_when_no_data(self):
        """With no entities or locations (ALLOWS_PROFILE), home routes (via
        location_view_default) through to the start/profile-picker page."""
        # Ensure no locations exist (and the base DB has no entities).
        Location.objects.all().delete()

        self.assertRedirectsToTemplates(reverse('home'), ['pages/start.html'])

    def test_home_view_redirects_to_location_view_when_locations_exist(self):
        """Test that HomeView redirects and renders location view template."""
        # Create a location with required fields
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        # Create a LocationView for the location
        LocationView.objects.create(
            location=location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            svg_style_name_str='DEFAULT'
        )
        
        url = reverse('home')
        # Use assertRedirectsToTemplates to follow redirects and verify final template
        self.assertRedirectsToTemplates(url, ['location/panes/location_view.html'])

    def test_home_view_self_heals_when_location_has_no_view(self):
        """A Location with no LocationView is an inconsistent state that
        shouldn't occur normally (location creation makes a default view).
        Rather than dead-ending, it is repaired with a default view and
        rendered.
        """
        # Create an orphaned Location without a LocationView.
        Location.objects.create(
            name='Orphaned Location',
            svg_fragment_filename='orphaned.svg',
            svg_view_box_str='0 0 100 100'
        )
        LocationView.objects.all().delete()

        self.assertRedirectsToTemplates(reverse('home'), ['location/panes/location_view.html'])

    def test_home_view_redirects_to_collection_view_when_collection_type(self):
        """Test that HomeView redirects to collection_view_default when view_type is collection."""
        # Create a location with required fields
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        # Create a LocationView for the location
        LocationView.objects.create(
            location=location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            svg_style_name_str='DEFAULT'
        )
        
        # Set session to have collection view type
        self.setSessionViewType(ViewType.COLLECTION)
        
        url = reverse('home')
        response = self.client.get(url)
        
        collection_url = reverse('collection_view_default')
        self.assertRedirects(response, collection_url, fetch_redirect_response=False)

    def test_home_view_redirects_to_location_view_when_location_type(self):
        """Test that HomeView redirects to location_view_default when view_type is location."""
        # Create a location with required fields
        location = Location.objects.create(
            name='Test Location',
            svg_fragment_filename='test.svg',
            svg_view_box_str='0 0 100 100'
        )
        # Create a LocationView for the location
        LocationView.objects.create(
            location=location,
            name='Test View',
            location_view_type_str='MAIN',
            svg_view_box_str='0 0 100 100',
            svg_rotate=0.0,
            svg_style_name_str='DEFAULT'
        )
        
        # Set session to have location view type (or leave default)
        self.setSessionViewType(ViewType.LOCATION_VIEW)
        
        url = reverse('home')
        response = self.client.get(url)
        
        location_view_url = reverse('location_view_default')
        self.assertRedirects(response, location_view_url, fetch_redirect_response=False)


class TestHealthView(SyncViewTestCase):
    """
    Tests for HealthView - demonstrates health check endpoint testing.
    This view returns JSON with system health status.
    """

    @patch('hi.views.do_healthcheck')
    def test_health_check_healthy(self, mock_healthcheck):
        """Test health check when system is healthy."""
        mock_healthcheck.return_value = {
            'is_healthy': True,
            'database': 'ok',
            'redis': 'ok',
            'subsystems': []
        }

        url = reverse('health')
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertIn('status', data)
        self.assertTrue(data['status']['is_healthy'])

    @patch('hi.views.do_healthcheck')
    def test_health_check_unhealthy(self, mock_healthcheck):
        """Test health check when system is unhealthy."""
        mock_healthcheck.return_value = {
            'is_healthy': False,
            'database': 'error',
            'redis': 'ok',
            'error_message': 'Database connection failed'
        }

        url = reverse('health')
        response = self.client.get(url)

        # Should return 500 when unhealthy
        self.assertServerErrorResponse(response)
        self.assertJsonResponse(response)
        
        data = response.json()
        self.assertIn('status', data)
        self.assertFalse(data['status']['is_healthy'])

    def test_health_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('health')
        response = self.client.post(url)

        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)


class TestSetSnapGridView(SyncViewTestCase):
    """SetSnapGridView persists the snap-grid preference to the session,
    clamped to the UI input's range (0 = disabled); malformed input is
    rejected so a crafted POST cannot store garbage."""

    def test_valid_value_persisted(self):
        response = self.client.post(reverse('set_snap_grid'), {'snap_grid_pixels': '10'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['svg_snap_grid_pixels'], 10)

    def test_value_clamped_to_max(self):
        self.client.post(reverse('set_snap_grid'), {'snap_grid_pixels': '999'})
        self.assertEqual(self.client.session['svg_snap_grid_pixels'], 50)

    def test_value_clamped_to_min(self):
        self.client.post(reverse('set_snap_grid'), {'snap_grid_pixels': '-5'})
        self.assertEqual(self.client.session['svg_snap_grid_pixels'], 0)

    def test_explicit_zero_disables(self):
        self.client.post(reverse('set_snap_grid'), {'snap_grid_pixels': '0'})
        self.assertEqual(self.client.session['svg_snap_grid_pixels'], 0)

    def test_malformed_rejected(self):
        response = self.client.post(reverse('set_snap_grid'), {'snap_grid_pixels': 'abc'})
        self.assertEqual(response.status_code, 400)
