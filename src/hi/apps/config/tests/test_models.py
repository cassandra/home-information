import logging
from django.db import IntegrityError

from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.attribute.enums import AttributeValueType
from hi.tests.base_test_case import BaseTestCase

logging.disable(logging.CRITICAL)


class TestSubsystem(BaseTestCase):

    def test_subsystem_unique_key_constraint(self):
        """Test subsystem_key uniqueness constraint - critical for data integrity."""
        Subsystem.objects.create(
            name='First Subsystem',
            subsystem_key='unique_key',
        )
        
        with self.assertRaises(IntegrityError):
            Subsystem.objects.create(
                name='Second Subsystem',
                subsystem_key='unique_key',  # Duplicate key should fail
            )
        return


class TestSubsystemAttribute(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.subsystem = Subsystem.objects.create(
            name='Test Subsystem',
            subsystem_key='test_subsystem',
        )
        return

    def test_subsystem_attribute_cascade_delete(self):
        """Test cascade deletion behavior - critical for data integrity."""
        attribute = SubsystemAttribute.objects.create(
            subsystem=self.subsystem,
            setting_key='test.setting.key',
            value_type=AttributeValueType.TEXT,
            value='test_value',
        )
        
        attribute_id = attribute.id
        self.assertTrue(SubsystemAttribute.objects.filter(id=attribute_id).exists())
        
        # Delete subsystem should cascade to attributes
        self.subsystem.delete()
        
        self.assertFalse(SubsystemAttribute.objects.filter(id=attribute_id).exists())
        return