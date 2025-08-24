import logging

from django.urls import reverse
from django.test import RequestFactory
from django.http import Http404

from hi.apps.console.views import EntityVideoStreamView
from hi.apps.entity.models import Entity
from hi.testing.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestEntityVideoStreamView(BaseTestCase):
    """Test EntityVideoStreamView for displaying video streams."""

    def setUp(self):
        super().setUp()
        
        # Create test entity with video stream capability
        self.video_entity = Entity.objects.create(
            integration_id='test.camera.front',
            integration_name='test_integration',
            name='Front Door Camera',
            entity_type_str='camera',
            has_video_stream=True
        )
        
        # Create entity without video stream capability  
        self.non_video_entity = Entity.objects.create(
            integration_id='test.sensor.temp',
            integration_name='test_integration',
            name='Temperature Sensor',
            entity_type_str='sensor', 
            has_video_stream=False
        )

    def test_get_main_template_name_returns_correct_template(self):
        """Test that the view returns the correct template name."""
        view = EntityVideoStreamView()
        template_name = view.get_main_template_name()
        
        self.assertEqual(template_name, 'console/panes/entity_video_pane.html')
        
    def test_view_integration_with_url_routing(self):
        """Test that the view integrates correctly with URL routing."""
        # This tests the actual URL pattern and view integration
        url = reverse('console_entity_video_stream', kwargs={'entity_id': self.video_entity.id})
        
        self.assertIn('/console/entity/video-stream/', url)
        self.assertIn(str(self.video_entity.id), url)
        
    def test_view_inheritance_from_higrideview(self):
        """Test that EntityVideoStreamView correctly inherits from HiGridView."""
        view = EntityVideoStreamView()
        
        # Should have HiGridView methods
        self.assertTrue(hasattr(view, 'get_main_template_name'))
        self.assertTrue(hasattr(view, 'get_main_template_context'))
        self.assertTrue(callable(view.get_main_template_name))
        self.assertTrue(callable(view.get_main_template_context))

    def test_view_class_exists_and_is_importable(self):
        """Test that the EntityVideoStreamView class exists and can be imported."""
        # This is a basic smoke test to ensure the view is properly defined
        from hi.apps.console.views import EntityVideoStreamView
        
        self.assertTrue(EntityVideoStreamView)
        self.assertTrue(hasattr(EntityVideoStreamView, 'get_main_template_name'))
        self.assertTrue(hasattr(EntityVideoStreamView, 'get_main_template_context'))

    def test_video_entity_has_correct_attributes(self):
        """Test that test video entity has correct attributes for testing."""
        self.assertEqual(self.video_entity.name, 'Front Door Camera')
        self.assertTrue(self.video_entity.has_video_stream)
        self.assertEqual(self.video_entity.integration_id, 'test.camera.front')

    def test_non_video_entity_has_correct_attributes(self):
        """Test that test non-video entity has correct attributes for testing."""
        self.assertEqual(self.non_video_entity.name, 'Temperature Sensor')
        self.assertFalse(self.non_video_entity.has_video_stream)
        self.assertEqual(self.non_video_entity.integration_id, 'test.sensor.temp')
