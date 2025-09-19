"""
Tests for ZoneMinder client factory functionality.
Focuses on high-value testing: client creation, validation, and error handling.
"""

from unittest.mock import Mock, patch
from django.test import TestCase

from hi.apps.system.enums import HealthStatusType
from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey, IntegrationValidationResult

from hi.services.zoneminder.enums import ZmAttributeType
from hi.services.zoneminder.zm_client_factory import ZmClientFactory
from hi.services.zoneminder.zm_metadata import ZmMetaData


class TestZmClientFactory(TestCase):
    """Test ZmClientFactory creation and validation behavior."""

    def setUp(self):
        self.factory = ZmClientFactory()

    def _create_test_attributes(self):
        """Create realistic test attributes for client creation."""
        attributes = {}

        # Create required attributes with realistic values
        attr_values = {
            ZmAttributeType.API_URL: 'https://zm.example.com/api',
            ZmAttributeType.PORTAL_URL: 'https://zm.example.com',
            ZmAttributeType.API_USER: 'test_user',
            ZmAttributeType.API_PASSWORD: 'test_password',
        }

        for attr_type, value in attr_values.items():
            integration_key = IntegrationKey(
                integration_id=ZmMetaData.integration_id,
                integration_name=str(attr_type),
            )

            # Create a realistic IntegrationAttribute mock
            attr = Mock(spec=IntegrationAttribute)
            attr.integration_key = integration_key
            attr.value = value
            attr.is_required = attr_type.is_required

            attributes[attr_type] = attr

        return attributes

    @patch('hi.services.zoneminder.zm_client_factory.ZMApi')
    def test_create_client_success(self, mock_zmapi_class):
        """Test successful client creation with valid attributes."""
        # Arrange
        mock_client = Mock()
        mock_zmapi_class.return_value = mock_client
        attributes = self._create_test_attributes()

        # Act
        result = self.factory.create_client(attributes)

        # Assert - Test the interface contract
        self.assertIs(result, mock_client)

        # Verify ZMApi was called with correct options
        expected_options = {
            'apiurl': 'https://zm.example.com/api',
            'portalurl': 'https://zm.example.com',
            'user': 'test_user',
            'password': 'test_password',
        }
        mock_zmapi_class.assert_called_once_with(options=expected_options)

    def test_create_client_missing_required_attribute(self):
        """Test client creation fails with missing required attribute."""
        # Arrange - missing API_URL
        attributes = self._create_test_attributes()
        del attributes[ZmAttributeType.API_URL]

        # Act & Assert
        with self.assertRaises(IntegrationAttributeError) as context:
            self.factory.create_client(attributes)

        # Verify the error provides useful context
        self.assertIn('Missing ZM API attribute', str(context.exception))
        self.assertIn('api_url', str(context.exception))

    def test_create_client_empty_attribute_value(self):
        """Test client creation fails with empty attribute value."""
        # Arrange
        attributes = self._create_test_attributes()
        attributes[ZmAttributeType.API_USER].value = '   '  # Empty/whitespace

        # Act & Assert
        with self.assertRaises(IntegrationAttributeError) as context:
            self.factory.create_client(attributes)

        # Verify the error provides useful context
        self.assertIn('Missing ZM API attribute value', str(context.exception))
        self.assertIn('api_user', str(context.exception))

    @patch('hi.services.zoneminder.pyzm_client.api.ZMApi')
    def test_test_client_success(self, mock_zmapi_class):
        """Test successful client connectivity testing."""
        # Arrange
        mock_client = Mock()
        mock_states_collection = Mock()
        mock_states_collection.list.return_value = [Mock(), Mock()]  # Some states
        mock_client.states.return_value = mock_states_collection

        # Act
        result = self.factory.test_client(mock_client)

        # Assert - Test actual behavior
        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.HEALTHY)
        self.assertIsNone(result.error_message)

        # Verify the client was actually tested
        mock_client.states.assert_called_once()
        mock_states_collection.list.assert_called_once()

    @patch('hi.services.zoneminder.pyzm_client.api.ZMApi')
    def test_test_client_connection_failure(self, mock_zmapi_class):
        """Test client testing with connection failure."""
        # Arrange
        mock_client = Mock()
        mock_client.states.side_effect = ConnectionError("Cannot connect to ZoneMinder")

        # Act
        result = self.factory.test_client(mock_client)

        # Assert - Test error handling behavior
        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.CONNECTION_ERROR)
        self.assertIn('Cannot connect to ZoneMinder', result.error_message)

    @patch('hi.services.zoneminder.pyzm_client.api.ZMApi')
    def test_test_client_authentication_failure(self, mock_zmapi_class):
        """Test client testing with authentication failure."""
        # Arrange
        mock_client = Mock()
        mock_client.states.side_effect = Exception("401 Unauthorized")

        # Act
        result = self.factory.test_client(mock_client)

        # Assert - Test error categorization
        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.CONNECTION_ERROR)
        self.assertIn('Authentication failed', result.error_message)

    @patch('hi.services.zoneminder.pyzm_client.api.ZMApi')
    def test_test_client_returns_none_states(self, mock_zmapi_class):
        """Test client testing when states call returns None."""
        # Arrange
        mock_client = Mock()
        mock_states_collection = Mock()
        mock_states_collection.list.return_value = None
        mock_client.states.return_value = mock_states_collection

        # Act
        result = self.factory.test_client(mock_client)

        # Assert
        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.CONNECTION_ERROR)
        self.assertIn('Failed to fetch states from ZoneMinder API', result.error_message)
        
