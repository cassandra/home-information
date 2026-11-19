import logging
from unittest.mock import Mock

from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, SimpleTestCase

from hi.apps.console.constants import ConsoleConstants
from hi.apps.console.device_capabilities import DeviceCapabilities, DeviceCapabilitiesCodec
from hi.apps.console.enums import DeviceCapability
from hi.apps.console.middleware import DeviceCapabilitiesMiddleware

logging.disable( logging.CRITICAL )

COOKIE_NAME = ConsoleConstants.DEVICE_CAPABILITIES_COOKIE_NAME


class TestDeviceCapabilities( SimpleTestCase ):

    def test_undeclared_capabilities_are_available( self ):
        device_capabilities = DeviceCapabilities()
        for capability in DeviceCapability:
            self.assertTrue( device_capabilities.is_available( capability ) )
            continue
        self.assertTrue( device_capabilities.is_default )
        return

    def test_declarations_merge_independently( self ):
        device_capabilities = DeviceCapabilities().with_declarations({
            DeviceCapability.KEYBOARD: False,
            DeviceCapability.LOCAL_FILES: False,
        }).with_declarations({
            DeviceCapability.LOCAL_FILES: True,
        })
        self.assertFalse( device_capabilities.is_available( DeviceCapability.KEYBOARD ) )
        self.assertTrue( device_capabilities.is_available( DeviceCapability.LOCAL_FILES ) )
        return

    def test_none_declaration_clears_to_default( self ):
        device_capabilities = DeviceCapabilities().with_declarations({
            DeviceCapability.KEYBOARD: False,
        }).with_declarations({
            DeviceCapability.KEYBOARD: None,
        })
        self.assertTrue( device_capabilities.is_default )
        return


class TestDeviceCapabilitiesCodec( SimpleTestCase ):

    def test_query_params_map_values_and_ignore_unrecognized( self ):
        declarations = DeviceCapabilitiesCodec.declarations_from_query_params({
            'keyboard': 'none',
            'browser_nav': 'default',
            'local_files': 'NONE',
            'other': 'none',
        })
        self.assertEqual( declarations, {
            DeviceCapability.KEYBOARD: False,
            DeviceCapability.BROWSER_NAV: None,
        })
        return

    def test_cookie_round_trip( self ):
        device_capabilities = DeviceCapabilities( declared = {
            DeviceCapability.KEYBOARD: False,
            DeviceCapability.BROWSER_NAV: True,
        })
        cookie_value = DeviceCapabilitiesCodec.to_cookie_value( device_capabilities )
        self.assertEqual( DeviceCapabilitiesCodec.from_cookie_value( cookie_value ),
                          device_capabilities )
        return

    def test_malformed_cookie_entries_are_ignored( self ):
        device_capabilities = DeviceCapabilitiesCodec.from_cookie_value(
            'keyboard:none|bogus:none|local_files:default|browser_nav|:'
        )
        self.assertEqual( device_capabilities.declared, { DeviceCapability.KEYBOARD: False } )
        return


class TestDeviceCapabilitiesMiddleware( SimpleTestCase ):

    def setUp( self ):
        super().setUp()
        self.factory = RequestFactory()
        return

    def _run( self, request, response = None ):
        get_response = Mock( return_value = response or HttpResponse( 'ok' ) )
        return DeviceCapabilitiesMiddleware( get_response )( request )

    def test_no_cookie_no_params_is_default_and_sets_no_cookie( self ):
        request = self.factory.get( '/' )
        response = self._run( request )
        self.assertTrue( request.device_capabilities.is_default )
        self.assertNotIn( COOKIE_NAME, response.cookies )
        return

    def test_params_merge_with_cookie_and_persist( self ):
        request = self.factory.get( '/', { 'local_files': 'none' } )
        request.COOKIES[ COOKIE_NAME ] = 'keyboard:none'
        response = self._run( request )

        self.assertFalse( request.device_capabilities.is_available( DeviceCapability.KEYBOARD ) )
        self.assertFalse( request.device_capabilities.is_available( DeviceCapability.LOCAL_FILES ) )
        persisted = DeviceCapabilitiesCodec.from_cookie_value( response.cookies[ COOKIE_NAME ].value )
        self.assertEqual( persisted, request.device_capabilities )
        return

    def test_cookie_without_params_is_read_but_not_rewritten( self ):
        request = self.factory.get( '/' )
        request.COOKIES[ COOKIE_NAME ] = 'browser_nav:none'
        response = self._run( request )
        self.assertFalse( request.device_capabilities.is_available( DeviceCapability.BROWSER_NAV ) )
        self.assertNotIn( COOKIE_NAME, response.cookies )
        return

    def test_clearing_last_declaration_deletes_cookie( self ):
        request = self.factory.get( '/', { 'keyboard': 'default' } )
        request.COOKIES[ COOKIE_NAME ] = 'keyboard:none'
        response = self._run( request )
        self.assertTrue( request.device_capabilities.is_default )
        self.assertEqual( response.cookies[ COOKIE_NAME ][ 'max-age' ], 0 )
        return

    def test_cookie_persisted_on_redirect_response( self ):
        """ A kiosk launch URL redirected (e.g., to sign-in) must still persist. """
        request = self.factory.get( '/', { 'keyboard': 'none' } )
        response = self._run( request, HttpResponseRedirect( '/user/signin' ) )
        self.assertIn( COOKIE_NAME, response.cookies )
        return
