"""Gateway tests: capability registration + validate_access probe.

Schema validation is exercised in detail in test_pl_validation; this
file covers the gateway's wiring to the referencer and the network
probe it runs for the "Test Connection" path.
"""
import logging
from unittest.mock import Mock, patch

from django.test import TestCase
from requests import RequestException

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.enums import IntegrationCapability
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.paperless.enums import PlAttributeType
from hi.services.paperless.integration import PaperlessGateway
from hi.services.paperless.pl_metadata import PaperlessMetaData
from hi.services.paperless.pl_referencer import PaperlessAttributeReferencer


logging.disable(logging.CRITICAL)


def _make_attr(integration, attr_type, value):
    attr = IntegrationAttribute(
        integration = integration,
        name = attr_type.label,
        value = value,
        value_type_str = str(AttributeValueType.TEXT),
        attribute_type_str = 'PREDEFINED',
    )
    attr.integration_key = IntegrationKey(
        integration_id = PaperlessMetaData.integration_id,
        integration_name = str(attr_type),
    )
    return attr


class TestPaperlessGatewayWiring(TestCase):

    def test_metadata_declares_attribute_reference(self):
        meta = PaperlessGateway().get_metadata()
        self.assertEqual(meta.integration_id, 'paperless')
        self.assertEqual(meta.label, 'Paperless-ngx')
        self.assertIn(IntegrationCapability.ATTRIBUTE_REFERENCE,
                      meta.capabilities)

    def test_returns_referencer(self):
        referencer = PaperlessGateway().get_attribute_referencer()
        self.assertIsInstance(referencer, PaperlessAttributeReferencer)


class TestValidateAccess(TestCase):

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id = PaperlessMetaData.integration_id,
            is_enabled = True,
        )
        self.attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL,
                       'https://paperless.example.com'),
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'token-abc'),
        ]

    @patch('hi.services.paperless.integration.requests.get')
    def test_200_response_returns_success(self, mock_get):
        mock_get.return_value = Mock(status_code = 200)
        result = PaperlessGateway().validate_access(
            integration_attributes = self.attrs,
            timeout_secs = 1.0,
        )
        self.assertTrue(result.is_success)
        # Probe issues a single tiny request — page_size=1 keeps the
        # upstream cost minimal.
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs['params']['page_size'], 1)
        self.assertEqual(kwargs['headers']['Authorization'], 'Token token-abc')

    @patch('hi.services.paperless.integration.requests.get')
    def test_401_returns_auth_failure(self, mock_get):
        mock_get.return_value = Mock(status_code = 401)
        result = PaperlessGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = 1.0,
        )
        self.assertFalse(result.is_success)
        self.assertIn('auth', result.message.lower())

    @patch('hi.services.paperless.integration.requests.get')
    def test_5xx_returns_failure(self, mock_get):
        mock_get.return_value = Mock(status_code = 503)
        result = PaperlessGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = 1.0,
        )
        self.assertFalse(result.is_success)
        self.assertIn('503', result.message)

    @patch('hi.services.paperless.integration.requests.get',
           side_effect = RequestException('refused'))
    def test_unreachable_returns_failure(self, _mock_get):
        result = PaperlessGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = 1.0,
        )
        self.assertFalse(result.is_success)
        self.assertIn('unreachable', result.message.lower())

    def test_schema_invalid_short_circuits(self):
        # When attributes don't even pass schema validation we must
        # not attempt the network call. patch.object on requests.get
        # asserts no call.
        bad_attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL, ''),
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'tok'),
        ]
        with patch('hi.services.paperless.integration.requests.get') as mock_get:
            result = PaperlessGateway().validate_access(
                integration_attributes = bad_attrs, timeout_secs = 1.0,
            )
        self.assertFalse(result.is_success)
        mock_get.assert_not_called()
