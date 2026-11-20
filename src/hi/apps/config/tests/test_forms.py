import logging

from hi.apps.attribute.enums import AttributeType, AttributeValueType
from hi.apps.config.forms import SubsystemAttributeForm
from hi.apps.config.models import Subsystem, SubsystemAttribute
from hi.apps.console.settings import ConsoleSetting
from hi.testing.base_test_case import BaseTestCase

logging.disable( logging.CRITICAL )


class TestSubsystemAttributeFormSettingValidator( BaseTestCase ):
    """ Uses the console lock PIN as a representative validated setting. """

    def setUp( self ):
        super().setUp()
        self.subsystem = Subsystem.objects.create(
            name = 'Test Subsystem',
            subsystem_key = 'test_subsystem',
        )
        return

    def _create_attribute( self, setting_key, value ):
        return SubsystemAttribute.objects.create(
            subsystem = self.subsystem,
            setting_key = setting_key,
            name = 'Test Setting',
            value = value,
            value_type_str = str( AttributeValueType.SECRET ),
            attribute_type_str = str( AttributeType.PREDEFINED ),
            is_editable = True,
            is_required = False,
        )

    def _bound_form( self, attribute, value ):
        return SubsystemAttributeForm(
            instance = attribute,
            data = { 'name': attribute.name, 'value': value },
        )

    def test_changed_invalid_value_is_rejected( self ):
        attribute = self._create_attribute( ConsoleSetting.CONSOLE_LOCK_PASSWORD.key, '' )
        form = self._bound_form( attribute, '12a' )
        self.assertFalse( form.is_valid() )
        self.assertIn( 'value', form.errors )
        return

    def test_changed_valid_value_is_accepted( self ):
        attribute = self._create_attribute( ConsoleSetting.CONSOLE_LOCK_PASSWORD.key, '' )
        form = self._bound_form( attribute, '1234' )
        self.assertTrue( form.is_valid(), form.errors )
        return

    def test_unchanged_legacy_value_does_not_block_save( self ):
        attribute = self._create_attribute( ConsoleSetting.CONSOLE_LOCK_PASSWORD.key, 'hunter2' )
        form = self._bound_form( attribute, 'hunter2' )
        self.assertTrue( form.is_valid(), form.errors )
        return

    def test_unresolvable_setting_key_skips_validation( self ):
        attribute = self._create_attribute( 'no.such.Setting.KEY', '' )
        form = self._bound_form( attribute, 'anything' )
        self.assertTrue( form.is_valid(), form.errors )
        return

