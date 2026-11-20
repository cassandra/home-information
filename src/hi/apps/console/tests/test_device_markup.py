import logging

from django.test import SimpleTestCase

from hi.apps.console.device_markup import device_requires_attrs
from hi.apps.console.enums import DeviceCapability, DeviceRequirementHandler
from hi.apps.console.templatetags import device_tags

logging.disable( logging.CRITICAL )


class TestDeviceRequiresAttrs( SimpleTestCase ):

    def test_handler_attr_rendered_only_when_handlers_given( self ):
        without_handlers = device_requires_attrs(
            [ DeviceCapability.KEYBOARD, DeviceCapability.LOCAL_FILES ],
        )
        self.assertEqual( without_handlers, 'data-requires="keyboard local_files"' )

        with_handlers = device_requires_attrs(
            [ DeviceCapability.KEYBOARD ],
            handlers = [ DeviceRequirementHandler.ON_SCREEN_KEYBOARD ],
        )
        self.assertEqual( with_handlers,
                          'data-requires="keyboard" data-requires-handler="on-screen-keyboard"' )

    def test_empty_declaration_fails( self ):
        with self.assertRaises( ValueError ):
            device_requires_attrs( [], handlers = [ DeviceRequirementHandler.ON_SCREEN_KEYBOARD ] )


class TestDeviceRequiresAttrsTag( SimpleTestCase ):

    def test_names_resolve_to_the_same_markup( self ):
        self.assertEqual(
            device_tags.device_requires_attrs( 'keyboard', handlers = 'on-screen-keyboard' ),
            device_requires_attrs( [ DeviceCapability.KEYBOARD ],
                                   handlers = [ DeviceRequirementHandler.ON_SCREEN_KEYBOARD ] ),
        )

    def test_unknown_names_fail( self ):
        with self.assertRaises( ValueError ):
            device_tags.device_requires_attrs( 'keybaord' )
        with self.assertRaises( ValueError ):
            device_tags.device_requires_attrs( 'keyboard', handlers = 'onscreen-keyboard' )
