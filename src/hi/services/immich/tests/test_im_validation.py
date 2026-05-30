import logging

from django.test import TestCase

from hi.apps.attribute.enums import AttributeValueType
from hi.apps.system.enums import HealthStatusType
from hi.integrations.models import Integration, IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey

from hi.services.immich.enums import ImAttributeType
from hi.services.immich.im_metadata import ImmichMetaData
from hi.services.immich.im_validation import validate_attributes


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


class TestValidateAttributes(TestCase):

    def setUp(self):
        self.integration = Integration.objects.create(
            integration_id = ImmichMetaData.integration_id,
            is_enabled = True,
        )

    def _all_valid(self):
        return [
            _make_attr(self.integration, ImAttributeType.API_URL,
                       'https://immich.example.com/'),
            _make_attr(self.integration, ImAttributeType.API_KEY, 'key-abc'),
        ]

    def test_all_present_and_valid_returns_success(self):
        result = validate_attributes(self._all_valid())
        self.assertTrue(result.is_valid)
        self.assertEqual(result.status, HealthStatusType.HEALTHY)

    def test_missing_api_url_returns_error(self):
        attrs = [
            _make_attr(self.integration, ImAttributeType.API_KEY, 'key-abc'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('API URL', result.error_message)

    def test_missing_api_key_returns_error(self):
        attrs = [
            _make_attr(self.integration, ImAttributeType.API_URL,
                       'https://immich.example.com/'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('API Key', result.error_message)

    def test_empty_value_treated_as_missing(self):
        attrs = [
            _make_attr(self.integration, ImAttributeType.API_URL, '   '),
            _make_attr(self.integration, ImAttributeType.API_KEY, 'key-abc'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('API URL', result.error_message)

    def test_invalid_scheme_returns_error(self):
        attrs = [
            _make_attr(self.integration, ImAttributeType.API_URL,
                       'ftp://immich.example.com/'),
            _make_attr(self.integration, ImAttributeType.API_KEY, 'key-abc'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('http(s)', result.error_message)

    def test_missing_netloc_returns_error(self):
        attrs = [
            _make_attr(self.integration, ImAttributeType.API_URL, 'https://'),
            _make_attr(self.integration, ImAttributeType.API_KEY, 'key-abc'),
        ]
        result = validate_attributes(attrs)
        self.assertFalse(result.is_valid)
        self.assertIn('hostname', result.error_message)
