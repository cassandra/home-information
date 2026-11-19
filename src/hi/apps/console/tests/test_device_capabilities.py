import logging
from unittest.mock import Mock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from hi.apps.console.constants import ConsoleConstants
from hi.apps.console.device_capabilities import DeviceCapabilities, DeviceCapabilitiesCodec
from hi.apps.console.enums import DeviceCapability
from hi.apps.console.middleware import DeviceCapabilitiesMiddleware
from hi.testing.base_test_case import BaseTestCase

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

    def test_reads_cookie_and_ignores_query_params( self ):
        request = RequestFactory().get( '/', { 'local_files': 'none' } )
        request.COOKIES[ COOKIE_NAME ] = 'keyboard:none'
        response = DeviceCapabilitiesMiddleware( Mock( return_value = HttpResponse( 'ok' ) ))( request )

        self.assertFalse( request.device_capabilities.is_available( DeviceCapability.KEYBOARD ) )
        self.assertTrue( request.device_capabilities.is_available( DeviceCapability.LOCAL_FILES ) )
        self.assertNotIn( COOKIE_NAME, response.cookies )
        return


class TestDeviceCapabilitiesView( BaseTestCase ):

    URL = reverse( 'console_device_capabilities' )

    def test_params_merge_with_cookie_persist_and_redirect_home( self ):
        self.client.cookies[ COOKIE_NAME ] = 'keyboard:none'
        response = self.client.get( self.URL, { 'local_files': 'none' } )

        self.assertRedirects( response, reverse( 'home' ), fetch_redirect_response = False )
        persisted = DeviceCapabilitiesCodec.from_cookie_value( response.cookies[ COOKIE_NAME ].value )
        self.assertEqual( persisted.declared, {
            DeviceCapability.KEYBOARD: False,
            DeviceCapability.LOCAL_FILES: False,
        })
        return

    def test_no_recognized_params_leaves_cookie_untouched( self ):
        self.client.cookies[ COOKIE_NAME ] = 'keyboard:none'
        response = self.client.get( self.URL, { 'keyboard': 'bogus' } )
        self.assertNotIn( COOKIE_NAME, response.cookies )
        return

    def test_clearing_last_declaration_deletes_cookie( self ):
        self.client.cookies[ COOKIE_NAME ] = 'keyboard:none'
        response = self.client.get( self.URL, { 'keyboard': 'default' } )
        self.assertEqual( response.cookies[ COOKIE_NAME ][ 'max-age' ], 0 )
        return

    @override_settings( SUPPRESS_AUTHENTICATION = False )
    def test_persists_when_signed_out( self ):
        """ A kiosk launch URL usually arrives before sign-in. """
        response = self.client.get( self.URL, { 'keyboard': 'none' } )
        self.assertRedirects( response, reverse( 'home' ), fetch_redirect_response = False )
        self.assertIn( COOKIE_NAME, response.cookies )
        return
