"""
Tests for Home Assistant client factory functionality.
Focuses on high-value testing: client creation, validation, and error handling.
"""

from unittest.mock import Mock, patch
from django.test import TestCase

from hi.integrations.enums import IntegrationHealthStatusType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey, IntegrationValidationResult

from hi.services.hass.enums import HassAttributeType
from hi.services.hass.hass_client import HassClient
from hi.services.hass.hass_client_factory import HassClientFactory
from hi.services.hass.hass_metadata import HassMetaData


class TestHassClientFactory(TestCase):
    """Test HassClientFactory creation and validation behavior."""

    def setUp(self):
        self.factory = HassClientFactory()

    def _create_test_attributes(self):
        """Create realistic test attributes for client creation."""
        attributes = {}

        # Create required attributes with realistic values
        attr_values = {
            HassAttributeType.API_BASE_URL: 'https://homeassistant.example.com:8123',
            HassAttributeType.API_TOKEN: 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_token',
        }

        for attr_type, value in attr_values.items():
            integration_key = IntegrationKey(
                integration_id=HassMetaData.integration_id,
                integration_name=str(attr_type),
            )

            # Create a realistic IntegrationAttribute mock
            attr = Mock(spec=IntegrationAttribute)
            attr.integration_key = integration_key
            attr.value = value
            attr.is_required = attr_type.is_required

            attributes[attr_type] = attr

        return attributes

    def test_create_client_success(self):
        """Test successful client creation with valid attributes."""
        # Arrange
        attributes = self._create_test_attributes()

        # Act
        result = self.factory.create_client(attributes)

        # Assert - Test the interface contract
        self.assertIsInstance(result, HassClient)

        # Verify client was configured correctly by checking internal state
        self.assertEqual(result._api_base_url, 'https://homeassistant.example.com:8123')
        self.assertIn('Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_token',
                      result._headers['Authorization'])

    def test_create_client_missing_required_attribute(self):
        """Test client creation fails with missing required attribute."""
        # Arrange - missing API_TOKEN
        attributes = self._create_test_attributes()
        del attributes[HassAttributeType.API_TOKEN]

        # Act & Assert
        with self.assertRaises(IntegrationAttributeError) as context:
            self.factory.create_client(attributes)

        # Verify the error provides useful context
        self.assertIn('Missing HASS API attribute', str(context.exception))
        self.assertIn('api_token', str(context.exception))

    def test_create_client_empty_attribute_value(self):
        """Test client creation fails with empty attribute value."""
        # Arrange
        attributes = self._create_test_attributes()
        attributes[HassAttributeType.API_BASE_URL].value = '   '  # Empty/whitespace

        # Act & Assert
        with self.assertRaises(IntegrationAttributeError) as context:
            self.factory.create_client(attributes)

        # Verify the error provides useful context
        self.assertIn('Missing HASS API attribute value', str(context.exception))
        self.assertIn('api_base_url', str(context.exception))

    @patch('hi.services.hass.hass_client.get')
    def test_test_client_success(self, mock_get):
        """Test successful client connectivity testing."""
        # Arrange
        mock_response = Mock()
        mock_response.text = '[{"entity_id": "sensor.test", "state": "on"}]'
        mock_get.return_value = mock_response

        attributes = self._create_test_attributes()
        client = self.factory.create_client(attributes)

        # Act
        result = self.factory.test_client(client)

        # Assert - Test actual behavior
        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.status, IntegrationHealthStatusType.HEALTHY)
        self.assertIsNone(result.error_message)

        # Verify the client was actually tested
        mock_get.assert_called_once()

    @patch('hi.services.hass.hass_client.get')
    def test_test_client_connection_failure(self, mock_get):
        """Test client testing with connection failure."""
        # Arrange
        mock_get.side_effect = ConnectionError("Connection refused")

        attributes = self._create_test_attributes()
        client = self.factory.create_client(attributes)

        # Act
        result = self.factory.test_client(client)

        # Assert - Test error handling behavior
        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, IntegrationHealthStatusType.CONNECTION_ERROR)
        self.assertIn('Cannot connect to Home Assistant', result.error_message)

    @patch('hi.services.hass.hass_client.get')
    def test_test_client_authentication_failure(self, mock_get):
        """Test client testing with authentication failure."""
        # Arrange
        mock_get.side_effect = Exception("401 Unauthorized - Invalid token")

        attributes = self._create_test_attributes()
        client = self.factory.create_client(attributes)

        # Act
        result = self.factory.test_client(client)

        # Assert - Test error categorization
        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, IntegrationHealthStatusType.CONNECTION_ERROR)
        self.assertIn('Authentication failed', result.error_message)
        
