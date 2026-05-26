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
        from hi.services.homebox.hb_client import HbClient as RealHbClient
        mock_client_class.API_URL = RealHbClient.API_URL
        mock_client_class.API_USER = RealHbClient.API_USER
        mock_client_class.API_PASSWORD = RealHbClient.API_PASSWORD

        mock_client = Mock()
        mock_client_class.return_value = mock_client
        attributes = self._create_test_attributes()

        result = self.factory.create_client(attributes)

        self.assertIs(result, mock_client)

        expected_options = {
            RealHbClient.API_URL: 'https://homebox.example.com/api',
            RealHbClient.API_USER: 'test_user',
            RealHbClient.API_PASSWORD: 'test_password',
        }
        mock_client_class.assert_called_once_with(
            api_options=expected_options, timeout_secs=None)

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
        """test_client succeeds when the lightweight items-summary probe returns a list."""
        mock_client = Mock()
        mock_client.get_items_summary.return_value = []

        result = self.factory.test_client(mock_client)

        self.assertIsInstance(result, IntegrationValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.HEALTHY)
        self.assertIsNone(result.error_message)

        # Probe must use the lightweight summary endpoint, not get_items
        # (which fetches per-item details).
        mock_client.get_items_summary.assert_called_once()
        mock_client.get_items.assert_not_called()

    def test_test_client_connection_failure(self):
        """Connection error from the probe surfaces with the connect category."""
        mock_client = Mock()
        mock_client.get_items_summary.side_effect = ConnectionError('Cannot connect to HomeBox')

        result = self.factory.test_client(mock_client)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.ERROR)
        self.assertIn('Cannot connect to HomeBox', result.error_message)

    def test_test_client_authentication_failure(self):
        """Auth error from the probe surfaces with the auth category."""
        mock_client = Mock()
        mock_client.get_items_summary.side_effect = Exception('401 Unauthorized')

        result = self.factory.test_client(mock_client)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.ERROR)
        self.assertIn('Authentication failed', result.error_message)

    def test_test_client_returns_none_items(self):
        """A None response from the probe is treated as a probe failure."""
        mock_client = Mock()
        mock_client.get_items_summary.return_value = None

        result = self.factory.test_client(mock_client)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.ERROR)
        self.assertIn('Failed to fetch items from HomeBox API', result.error_message)

        mock_client.get_items_summary.assert_called_once()

    @patch('hi.services.homebox.hb_client_factory.HbClient')
    def test_create_client_threads_timeout_to_client(self, mock_client_class):
        """create_client passes timeout_secs through to the HbClient."""
        from hi.services.homebox.hb_client import HbClient as RealHbClient
        mock_client_class.API_URL = RealHbClient.API_URL
        mock_client_class.API_USER = RealHbClient.API_USER
        mock_client_class.API_PASSWORD = RealHbClient.API_PASSWORD

        attributes = self._create_test_attributes()
        self.factory.create_client(attributes, timeout_secs=2)

        kwargs = mock_client_class.call_args.kwargs
        self.assertEqual(kwargs.get('timeout_secs'), 2)


class TestHbClientFactoryResolveBackend(TestCase):
    """Version-probe selection: ``GET /v1/entities`` is the
    discriminator. 2xx selects the entities backend, 404 falls
    back to the legacy backend, other errors propagate so the
    manager can record an error state and retry later."""

    def _api_options(self):
        from hi.services.homebox.hb_client import HbClient
        return {
            HbClient.API_URL: 'https://homebox.local',
            HbClient.API_USER: 'user',
            HbClient.API_PASSWORD: 'pass',
        }

    def test_entities_200_selects_entities_backend(self):
        from hi.services.homebox.hb_client_backends import (
            _HbEntitiesBackend, _HbLegacyBackend,
        )
        with patch.object(_HbLegacyBackend, '_login'):
            with patch.object(
                _HbLegacyBackend, '_make_request', return_value={'items': []}
            ):
                backend = HbClientFactory.resolve_backend(
                    api_options=self._api_options(),
                )
        self.assertIsInstance(backend, _HbEntitiesBackend)

    def test_entities_404_falls_back_to_legacy(self):
        from requests import HTTPError, Response
        from hi.services.homebox.hb_client_backends import _HbLegacyBackend
        response = Mock(spec=Response)
        response.status_code = 404
        http_error = HTTPError('Not Found')
        http_error.response = response

        with patch.object(_HbLegacyBackend, '_login'):
            with patch.object(
                _HbLegacyBackend, '_make_request', side_effect=http_error
            ):
                backend = HbClientFactory.resolve_backend(
                    api_options=self._api_options(),
                )
        self.assertIsInstance(backend, _HbLegacyBackend)

    def test_non_404_http_error_propagates(self):
        from requests import HTTPError, Response
        from hi.services.homebox.hb_client_backends import _HbLegacyBackend
        response = Mock(spec=Response)
        response.status_code = 500
        http_error = HTTPError('Server Error')
        http_error.response = response

        with patch.object(_HbLegacyBackend, '_login'):
            with patch.object(
                _HbLegacyBackend, '_make_request', side_effect=http_error
            ):
                with self.assertRaises(HTTPError):
                    HbClientFactory.resolve_backend(
                        api_options=self._api_options(),
                    )

