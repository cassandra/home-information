import logging

from django.urls import reverse

from hi.apps.console.enums import DeviceCapability
from hi.testing.view_test_base import DualModeViewTestCase

logging.disable( logging.CRITICAL )


class TestDeviceCapabilityUnavailableView( DualModeViewTestCase ):

    def _get_modal_html( self, requires ):
        url = reverse( 'console_device_capability_unavailable' )
        response = self.async_get( url, { 'requires': requires } )
        self.assertSuccessResponse( response )
        return response.json()[ 'modal' ]

    def test_shows_reason_for_each_requested_capability_only( self ):
        modal_html = self._get_modal_html([ 'local_files', 'browser_nav', 'bogus' ])
        self.assertIn( DeviceCapability.LOCAL_FILES.description, modal_html )
        self.assertIn( DeviceCapability.BROWSER_NAV.description, modal_html )
        self.assertNotIn( DeviceCapability.KEYBOARD.description, modal_html )
        return

    def test_no_recognized_capability_shows_generic_message( self ):
        modal_html = self._get_modal_html([ 'bogus' ])
        self.assertIn( 'This action is not available on this device.', modal_html )
        return
