"""Schema-only validation for paperless integration attributes.

Validation is shared between the gateway's
``validate_configuration`` and the referencer's, so tests target the
helper directly. Network probes belong to ``validate_access`` —
covered separately.
"""
import logging

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.system.enums import HealthStatusType
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.paperless.enums import PlAttributeType
from hi.services.paperless.pl_metadata import PaperlessMetaData
from hi.services.paperless.pl_validation import validate_attributes


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


class TestValidateAttributes(TestCase):

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id = PaperlessMetaData.integration_id,
            is_enabled = True,
        )

    def test_all_present_and_valid_returns_success(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL,
                       'https://paperless.example.com/'),
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'token-abc'),
        ]
        result = validate_attributes(attrs)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.HEALTHY)

    def test_missing_api_url_returns_error(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'token-abc'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('API URL', result.error_message)

    def test_missing_token_returns_error(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL,
                       'https://paperless.example.com/'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('API Token', result.error_message)

    def test_empty_value_treated_as_missing(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL, '   '),
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'token-abc'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('API URL', result.error_message)

    def test_invalid_scheme_returns_error(self):
        # File / FTP / scheme-less URLs are rejected; the client uses
        # requests' HTTP-only session, so allowing them would surface
        # as a cryptic runtime failure rather than a config-time one.
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL,
                       'ftp://paperless.example.com/'),
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'token'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('http(s)', result.error_message)

    def test_missing_netloc_returns_error(self):
        attrs = [
            _make_attr(self.integration, PlAttributeType.API_URL, 'https://'),
            _make_attr(self.integration, PlAttributeType.API_TOKEN, 'token'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('hostname', result.error_message)
