import logging
from django.db import IntegrityError

from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.attribute.enums import AttributeValueType
from hi.testing.base_test_case import BaseTestCase

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

    def test_subsystem_string_representation(self):
        """Test subsystem string representation uses subsystem_key."""
        subsystem = Subsystem.objects.create(
            name='Weather System',
            subsystem_key='weather_sys',
        )
        
        self.assertEqual(str(subsystem), 'weather_sys')
        return

    def test_subsystem_attribute_relationship(self):
        """Test subsystem can access its attributes through relationship."""
        subsystem = Subsystem.objects.create(
            name='Test Subsystem',
            subsystem_key='test_subsystem',
        )
        
        # Create multiple attributes
        attr1 = SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key='test.setting.one',
            value_type=AttributeValueType.TEXT,
            value='value_one',
        )
        attr2 = SubsystemAttribute.objects.create(
            subsystem=subsystem,
            setting_key='test.setting.two',
            value_type=AttributeValueType.INTEGER,
            value='42',
        )
        
        # Test relationship access
        attributes = subsystem.attributes.all()
        self.assertEqual(len(attributes), 2)
        self.assertIn(attr1, attributes)
        self.assertIn(attr2, attributes)
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

    def test_attribute_value_storage_and_retrieval(self):
        """Test attribute values are stored and retrieved correctly across different types."""
        test_cases = [
            (AttributeValueType.TEXT, 'text_value'),
            (AttributeValueType.INTEGER, '123'),
            (AttributeValueType.FLOAT, '3.14159'),
            (AttributeValueType.BOOLEAN, 'true'),
            (AttributeValueType.ENUM, 'OPTION_A'),
        ]
        
        for value_type, test_value in test_cases:
            with self.subTest(value_type=value_type):
                attribute = SubsystemAttribute.objects.create(
                    subsystem=self.subsystem,
                    setting_key=f'test.{value_type.name.lower()}.key',
                    value_type=value_type,
                    value=test_value,
                )
                
                # Reload from database to ensure persistence
                attribute.refresh_from_db()
                self.assertEqual(attribute.value, test_value)
                self.assertEqual(attribute.value_type, value_type)
        return

    def test_attribute_upload_path_configuration(self):
        """Test attribute upload path is correctly configured for settings."""
        attribute = SubsystemAttribute.objects.create(
            subsystem=self.subsystem,
            setting_key='test.file.setting',
            value_type=AttributeValueType.FILE,
            value='test_file.txt',
        )
        
        upload_path = attribute.get_upload_to()
        self.assertEqual(upload_path, 'settings/')
        return

    def test_attribute_setting_key_flexibility(self):
        """Test setting keys support various naming conventions."""
        key_formats = [
            'simple.key',
            'complex.nested.setting.key',
            'module.class.CONSTANT_NAME',
            'app.config.user_preference',
        ]
        
        for setting_key in key_formats:
            with self.subTest(setting_key=setting_key):
                attribute = SubsystemAttribute.objects.create(
                    subsystem=self.subsystem,
                    setting_key=setting_key,
                    value_type=AttributeValueType.TEXT,
                    value='test_value',
                )
                
                self.assertEqual(attribute.setting_key, setting_key)
        return
