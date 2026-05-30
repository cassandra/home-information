import logging
from unittest.mock import Mock, patch

from django.test import TestCase
from requests import RequestException

from hi.apps.attribute.enums import AttributeValueType
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.immich.enums import ImAttributeType
from hi.services.immich.integration import ImmichGateway
from hi.services.immich.im_metadata import ImmichMetaData


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
        integration_id = ImmichMetaData.integration_id,
        integration_name = str(attr_type),
    )
    return attr


class TestValidateAccess(TestCase):

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id = ImmichMetaData.integration_id,
            is_enabled = True,
        )
        self.attrs = [
            _make_attr(self.integration, ImAttributeType.API_URL,
                       'https://immich.example.com'),
            _make_attr(self.integration, ImAttributeType.API_KEY, 'key-abc'),
        ]

    @patch('hi.services.immich.integration.requests.post')
    def test_200_response_returns_success(self, mock_post):
        mock_post.return_value = Mock(status_code = 200)
        result = ImmichGateway().validate_access(
            integration_attributes = self.attrs,
            timeout_secs = 1.0,
        )
        self.assertTrue(result.is_success)
        args, kwargs = mock_post.call_args
        # Probe hits the cheap metadata endpoint (no CLIP embedding)
        # but exercises the same asset.read scope as smart search.
        self.assertEqual(args[0], 'https://immich.example.com/api/search/metadata')
        self.assertEqual(kwargs['json'], {'size': 1})
        self.assertEqual(kwargs['headers']['x-api-key'], 'key-abc')
        self.assertEqual(kwargs['timeout'], 1.0)

    @patch('hi.services.immich.integration.requests.post')
    def test_401_returns_key_not_recognized(self, mock_post):
        mock_post.return_value = Mock(status_code = 401)
        result = ImmichGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = 1.0,
        )
        self.assertFalse(result.is_success)
        self.assertIn('not recognized', result.message)

    @patch('hi.services.immich.integration.requests.post')
    def test_403_names_asset_read_scope(self, mock_post):
        mock_post.return_value = Mock(status_code = 403)
        result = ImmichGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = 1.0,
        )
        self.assertFalse(result.is_success)
        self.assertIn('asset.read', result.message)

    @patch('hi.services.immich.integration.requests.post')
    def test_5xx_returns_status_code(self, mock_post):
        mock_post.return_value = Mock(status_code = 503)
        result = ImmichGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = 1.0,
        )
        self.assertFalse(result.is_success)
        self.assertIn('503', result.message)

    @patch('hi.services.immich.integration.requests.post',
           side_effect = RequestException('refused'))
    def test_unreachable_returns_failure(self, _mock_post):
        result = ImmichGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = 1.0,
        )
        self.assertFalse(result.is_success)
        self.assertIn('unreachable', result.message.lower())

    def test_schema_invalid_short_circuits_no_network_call(self):
        bad_attrs = [
            _make_attr(self.integration, ImAttributeType.API_URL, ''),
            _make_attr(self.integration, ImAttributeType.API_KEY, 'k'),
        ]
        with patch('hi.services.immich.integration.requests.post') as mock_post:
            result = ImmichGateway().validate_access(
                integration_attributes = bad_attrs, timeout_secs = 1.0,
            )
        self.assertFalse(result.is_success)
        mock_post.assert_not_called()

    @patch('hi.services.immich.integration.requests.post')
    def test_default_timeout_when_none(self, mock_post):
        mock_post.return_value = Mock(status_code = 200)
        ImmichGateway().validate_access(
            integration_attributes = self.attrs, timeout_secs = None,
        )
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs['timeout'], 5.0)
