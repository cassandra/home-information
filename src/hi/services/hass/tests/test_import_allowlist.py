import logging
from unittest.mock import Mock

from django.test import SimpleTestCase

from hi.services.hass.hass_converter import HassConverter

logging.disable( logging.CRITICAL )


class TestParseImportAllowlist( SimpleTestCase ):

    def test_parse_domain_only_rules( self ):
        allowlist = 'light\nswitch\nsensor'
        domains, domain_classes = HassConverter.parse_import_allowlist( allowlist )

        self.assertEqual( domains, { 'light', 'switch', 'sensor' } )
        self.assertEqual( domain_classes, set() )
        return

    def test_parse_domain_class_rules( self ):
        allowlist = 'sensor:temperature\nbinary_sensor:motion'
        domains, domain_classes = HassConverter.parse_import_allowlist( allowlist )

        self.assertEqual( domains, set() )
        self.assertEqual( domain_classes, {
            ( 'sensor', 'temperature' ),
            ( 'binary_sensor', 'motion' ),
        } )
        return

    def test_parse_mixed_rules( self ):
        allowlist = 'light\nsensor:temperature\nswitch\nbinary_sensor:door'
        domains, domain_classes = HassConverter.parse_import_allowlist( allowlist )

        self.assertEqual( domains, { 'light', 'switch' } )
        self.assertEqual( domain_classes, {
            ( 'sensor', 'temperature' ),
            ( 'binary_sensor', 'door' ),
        } )
        return

    def test_parse_ignores_blank_lines( self ):
        allowlist = 'light\n\n\nswitch\n  \n'
        domains, domain_classes = HassConverter.parse_import_allowlist( allowlist )

        self.assertEqual( domains, { 'light', 'switch' } )
        return

    def test_parse_strips_whitespace( self ):
        allowlist = '  light  \n  sensor:temperature  '
        domains, domain_classes = HassConverter.parse_import_allowlist( allowlist )

        self.assertEqual( domains, { 'light' } )
        self.assertEqual( domain_classes, { ( 'sensor', 'temperature' ) } )
        return


class TestIsStateAllowed( SimpleTestCase ):

    def _mock_state( self, domain, device_class = None ):
        state = Mock()
        state.domain = domain
        state.device_class = device_class
        return state

    def test_domain_match_allows_state( self ):
        state = self._mock_state( 'light' )
        self.assertTrue( HassConverter.is_state_allowed(
            state, { 'light', 'switch' }, set(),
        ) )
        return

    def test_domain_not_in_allowlist_rejects_state( self ):
        state = self._mock_state( 'automation' )
        self.assertFalse( HassConverter.is_state_allowed(
            state, { 'light', 'switch' }, set(),
        ) )
        return

    def test_domain_class_match_allows_state( self ):
        state = self._mock_state( 'sensor', device_class = 'temperature' )
        self.assertTrue( HassConverter.is_state_allowed(
            state, set(), { ( 'sensor', 'temperature' ) },
        ) )
        return

    def test_domain_class_mismatch_rejects_state( self ):
        state = self._mock_state( 'sensor', device_class = 'diagnostic' )
        self.assertFalse( HassConverter.is_state_allowed(
            state, set(), { ( 'sensor', 'temperature' ) },
        ) )
        return

    def test_full_domain_allows_any_class( self ):
        state = self._mock_state( 'sensor', device_class = 'anything' )
        self.assertTrue( HassConverter.is_state_allowed(
            state, { 'sensor' }, set(),
        ) )
        return

    def test_no_device_class_with_domain_class_rule_rejects( self ):
        state = self._mock_state( 'sensor', device_class = None )
        self.assertFalse( HassConverter.is_state_allowed(
            state, set(), { ( 'sensor', 'temperature' ) },
        ) )
        return
