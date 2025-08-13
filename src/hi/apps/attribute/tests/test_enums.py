import logging

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestAttributeType(BaseTestCase):

    def test_attribute_type_deletion_policy(self):
        """Test AttributeType deletion policy - critical for data safety."""
        # Only CUSTOM attributes should be deletable
        self.assertTrue(AttributeType.CUSTOM.can_delete)
        self.assertFalse(AttributeType.PREDEFINED.can_delete)
        return


class TestAttributeValueType(BaseTestCase):

    def test_attribute_value_type_default_fallback(self):
        """Test AttributeValueType default fallback - critical for initialization."""
        self.assertEqual(AttributeValueType.default(), AttributeValueType.TEXT)
        return