import logging
from unittest.mock import Mock

from django.test import SimpleTestCase

from hi.integrations.exceptions import IntegrationAttributeError
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import IntegrationKey
from hi.services.homebox.enums import HbAttributeType
from hi.services.homebox.hb_manager import HomeBoxManager
from hi.services.homebox.hb_metadata import HbMetaData


logging.disable(logging.CRITICAL)


class TestHomeBoxManagerAttributeMap(SimpleTestCase):

    def setUp(self):
        self.manager = HomeBoxManager.__new__(HomeBoxManager)

    def _mock_attribute(self, hb_attr_type: HbAttributeType, value: str):
        attr = Mock(spec=IntegrationAttribute)
        attr.integration_key = IntegrationKey(
            integration_id=HbMetaData.integration_id,
            integration_name=str(hb_attr_type),
        )
        attr.value = value
        attr.is_required = hb_attr_type.is_required
        return attr

    def test_build_map_returns_all_required_attributes_when_valid(self):
        attrs = [
            self._mock_attribute(HbAttributeType.API_URL, 'https://homebox.local/api'),
            self._mock_attribute(HbAttributeType.API_USER, 'user'),
            self._mock_attribute(HbAttributeType.API_PASSWORD, 'secret'),
        ]

        result = self.manager._build_hb_attr_type_to_attribute_map(
            integration_attributes=attrs,
            enforce_requirements=True,
        )

        self.assertEqual(set(result.keys()), set(HbAttributeType))

    def test_build_map_raises_when_required_attribute_missing_and_enforced(self):
        attrs = [
            self._mock_attribute(HbAttributeType.API_URL, 'https://homebox.local/api'),
            self._mock_attribute(HbAttributeType.API_USER, 'user'),
        ]

        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager._build_hb_attr_type_to_attribute_map(
                integration_attributes=attrs,
                enforce_requirements=True,
            )

        self.assertIn('Missing HomeBox attribute', str(context.exception))
        self.assertIn('api_password', str(context.exception))

    def test_build_map_allows_missing_when_requirements_not_enforced(self):
        attrs = [
            self._mock_attribute(HbAttributeType.API_URL, 'https://homebox.local/api'),
        ]

        result = self.manager._build_hb_attr_type_to_attribute_map(
            integration_attributes=attrs,
            enforce_requirements=False,
        )

        self.assertEqual(set(result.keys()), {HbAttributeType.API_URL})

    def test_build_map_raises_when_required_value_is_blank_and_enforced(self):
        attrs = [
            self._mock_attribute(HbAttributeType.API_URL, 'https://homebox.local/api'),
            self._mock_attribute(HbAttributeType.API_USER, '   '),
            self._mock_attribute(HbAttributeType.API_PASSWORD, 'secret'),
        ]

        with self.assertRaises(IntegrationAttributeError) as context:
            self.manager._build_hb_attr_type_to_attribute_map(
                integration_attributes=attrs,
                enforce_requirements=True,
            )

        self.assertIn('Missing HomeBox attribute value', str(context.exception))
        self.assertIn('api_user', str(context.exception))
