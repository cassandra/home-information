import logging
from unittest.mock import Mock, patch

from django.urls import reverse

from hi.apps.attribute.models import AttributeModel
from hi.apps.entity.models import Entity, EntityAttribute
from hi.testing.view_test_base import SyncViewTestCase, DualModeViewTestCase

logging.disable(logging.CRITICAL)


class TestAttributeHistoryView(DualModeViewTestCase):
    """
    Tests for AttributeHistoryView - displays attribute value history in a modal.
    This view shows historical changes and allows restoring previous values.
    """

    def setUp(self):
        super().setUp()
        # Create test entity
        self.entity = Entity.objects.create(
            integration_id='test.entity',
            integration_name='test_integration',
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        # Create test attribute
        self.attribute = EntityAttribute.objects.create(
            entity=self.entity,
            name='brightness',
            value='100',
            attribute_type_str='TEXT'
        )

    def test_get_history_sync(self):
        """Test getting attribute history with synchronous request."""
        url = reverse('attribute_history', kwargs={'attribute_id': self.attribute.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        self.assertTemplateRendered(response, 'attribute/modals/attribute_history.html')
        
        # Verify context data
        self.assertEqual(response.context['attribute'], self.attribute)
        self.assertIn('history_records', response.context)

    def test_get_history_async(self):
        """Test getting attribute history with AJAX request."""
        url = reverse('attribute_history', kwargs={'attribute_id': self.attribute.id})
        response = self.async_get(url)

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        self.assertTemplateRendered(response, 'attribute/modals/attribute_history.html')

    @patch.object(AttributeModel, '_get_history_model_class')
    def test_history_with_no_history_model(self, mock_get_history_model):
        """Test history view when attribute has no history model."""
        mock_get_history_model.return_value = None
        
        url = reverse('attribute_history', kwargs={'attribute_id': self.attribute.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertHtmlResponse(response)
        
        # Should show empty history
        self.assertEqual(len(response.context['history_records']), 0)

    @patch.object(AttributeModel, '_get_history_model_class')
    def test_history_with_records(self, mock_get_history_model):
        """Test history view with actual history records."""
        # Mock history model and records
        mock_history_model = Mock()
        mock_get_history_model.return_value = mock_history_model
        
        mock_record = Mock()
        mock_record.pk = 1
        mock_record.value = '75'
        mock_record.changed_datetime = Mock()
        
        mock_history_model.objects.filter.return_value.order_by.return_value.__getitem__.return_value = [mock_record]
        
        url = reverse('attribute_history', kwargs={'attribute_id': self.attribute.id})
        response = self.client.get(url)

        self.assertSuccessResponse(response)
        self.assertEqual(response.context['attribute'], self.attribute)
        self.assertEqual(list(response.context['history_records']), [mock_record])

    def test_nonexistent_attribute_returns_404(self):
        """Test that accessing nonexistent attribute returns 404."""
        url = reverse('attribute_history', kwargs={'attribute_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed."""
        url = reverse('attribute_history', kwargs={'attribute_id': self.attribute.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 405)


class TestAttributeRestoreView(SyncViewTestCase):
    """
    Tests for AttributeRestoreView - restores attribute values from history.
    This view handles POST requests to restore previous attribute values.
    """

    def setUp(self):
        super().setUp()
        # Create test entity
        self.entity = Entity.objects.create(
            integration_id='test.entity',
            integration_name='test_integration',
            name='Test Entity',
            entity_type_str='LIGHT'
        )
        # Create test attribute
        self.attribute = EntityAttribute.objects.create(
            entity=self.entity,
            name='brightness',
            value='100',
            attribute_type_str='TEXT'
        )

    @patch.object(AttributeModel, '_get_history_model_class')
    def test_restore_with_valid_history_record(self, mock_get_history_model):
        """Test successful restore with valid history record."""
        # Mock history model and record
        mock_history_model = Mock()
        mock_get_history_model.return_value = mock_history_model
        
        mock_history_record = Mock()
        mock_history_record.value = '75'
        mock_history_model.objects.get.return_value = mock_history_record
        
        url = reverse('attribute_restore', kwargs={'attribute_id': self.attribute.id})
        response = self.client.post(url, {'history_id': '1'})

        self.assertSuccessResponse(response)
        self.assertJsonResponse(response)
        
        # Verify attribute was updated
        self.attribute.refresh_from_db()
        self.assertEqual(self.attribute.value, '75')

    @patch.object(AttributeModel, '_get_history_model_class')  
    def test_restore_with_no_history_model(self, mock_get_history_model):
        """Test restore when attribute has no history model."""
        mock_get_history_model.return_value = None
        
        url = reverse('attribute_restore', kwargs={'attribute_id': self.attribute.id})
        response = self.client.post(url, {'history_id': '1'})

        self.assertEqual(response.status_code, 404)

    def test_restore_without_history_id(self):
        """Test restore request without history_id parameter."""
        url = reverse('attribute_restore', kwargs={'attribute_id': self.attribute.id})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 404)

    @patch.object(AttributeModel, '_get_history_model_class')
    def test_restore_with_nonexistent_history_record(self, mock_get_history_model):
        """Test restore with non-existent history record."""
        mock_history_model = Mock()
        mock_get_history_model.return_value = mock_history_model
        mock_history_model.DoesNotExist = Exception
        mock_history_model.objects.get.side_effect = mock_history_model.DoesNotExist()
        
        url = reverse('attribute_restore', kwargs={'attribute_id': self.attribute.id})
        response = self.client.post(url, {'history_id': '999'})

        self.assertEqual(response.status_code, 404)

    def test_restore_nonexistent_attribute_returns_404(self):
        """Test that restoring nonexistent attribute returns 404."""
        url = reverse('attribute_restore', kwargs={'attribute_id': 99999})
        response = self.client.post(url, {'history_id': '1'})

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        """Test that GET requests are not allowed."""
        url = reverse('attribute_restore', kwargs={'attribute_id': self.attribute.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
