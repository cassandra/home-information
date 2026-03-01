"""
Tests for HomeBox client factory functionality.
Focuses on high-value testing: client creation, validation, and error handling.
"""

import logging
from unittest.mock import Mock, patch
from django.test import TestCase

from hi.apps.system.enums import HealthStatusType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey, IntegrationValidationResult

from hi.services.homebox.enums import HbAttributeType
from hi.services.homebox.hb_client_factory import HbClientFactory
from hi.services.homebox.hb_metadata import HbMetaData

logging.disable(logging.CRITICAL)


class TestHbClientFactory(TestCase):
    """Test HbClientFactory creation and validation behavior."""

    def setUp(self):
        self.factory = HbClientFactory()

    def _create_test_attributes(self):
        """Create realistic test attributes for client creation."""
        attributes = {}

        attr_values = {
            HbAttributeType.API_URL: 'https://homebox.example.com/api',
            HbAttributeType.API_USER: 'test_user',
            HbAttributeType.API_PASSWORD: 'test_password',
        }

        for attr_type, value in attr_values.items():
            integration_key = IntegrationKey(
                integration_id=HbMetaData.integration_id,
                integration_name=str(attr_type),
            )

            attr = Mock(spec=IntegrationAttribute)
            attr.integration_key = integration_key
            attr.value = value
            attr.is_required = attr_type.is_required

            attributes[attr_type] = attr

        return attributes

    @patch('hi.services.homebox.hb_client_factory.HbClient')
    def test_create_client_success(self, mock_client_class):
        """Test successful client creation with valid attributes."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        attributes = self._create_test_attributes()

        result = self.factory.create_client(attributes)

        self.assertIs(result, mock_client)

        expected_options = {
            'apiurl': 'https://homebox.example.com/api',
            'user': 'test_user',
            'password': 'test_password',
        }
        mock_client_class.assert_called_once_with(api_options=expected_options)

    def test_create_client_missing_required_attribute(self):
        """Test client creation fails with missing required attribute."""
        attributes = self._create_test_attributes()
        del attributes[HbAttributeType.API_URL]

        with self.assertRaises(IntegrationAttributeError) as context:
            self.factory.create_client(attributes)

        self.assertIn('Missing HB API attribute', str(context.exception))
        self.assertIn('api_url', str(context.exception))

    def test_create_client_empty_attribute_value(self):
        """Test client creation fails with empty attribute value."""
        attributes = self._create_test_attributes()
        attributes[HbAttributeType.API_USER].value = '   '

        with self.assertRaises(IntegrationAttributeError) as context:
            self.factory.create_client(attributes)

        self.assertIn('Missing HB API attribute value', str(context.exception))
        self.assertIn('api_user', str(context.exception))

    def test_test_client_success(self):
        """Test successful client connectivity testing."""
        mock_client = Mock()
        mock_client.get_items.return_value = []

        result = self.factory.test_client(mock_client)

        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.HEALTHY)
        self.assertIsNone(result.error_message)

        mock_client.get_items.assert_called_once()

    def test_test_client_connection_failure(self):
        """Test client testing with connection failure."""
        mock_client = Mock()
        mock_client.get_items.side_effect = ConnectionError('Cannot connect to HomeBox')

        result = self.factory.test_client(mock_client)

        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.ERROR)
        self.assertIn('Cannot connect to HomeBox', result.error_message)

    def test_test_client_authentication_failure(self):
        """Test client testing with authentication failure."""
        mock_client = Mock()
        mock_client.get_items.side_effect = Exception('401 Unauthorized')

        result = self.factory.test_client(mock_client)

        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.ERROR)
        self.assertIn('Authentication failed', result.error_message)

    def test_test_client_returns_none_items(self):
        """Test client testing when items call returns None."""
        mock_client = Mock()
        mock_client.get_items.return_value = None

        result = self.factory.test_client(mock_client)

        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.ERROR)
        self.assertIn('Failed to fetch items from HomeBox API', result.error_message)

        mock_client.get_items.assert_called_once()
