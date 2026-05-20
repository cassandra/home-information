"""Tests for ``FrigateController.do_control`` — the bridge between
HI's controller invocation surface and Frigate's HTTP control API.

Covers the per-camera detect on/off command path:
  * HI lowercase ``on`` / ``off`` translates to Frigate-side
    ``ON`` / ``OFF`` via the explicit converter mapping.
  * Manager errors surface as ``error_list`` entries.
  * Unknown integration_name shapes / unknown HI values surface as
    clean errors rather than half-formed wire calls.
"""
import logging
from unittest.mock import Mock

from django.test import TestCase

from hi.integrations.transient_models import IntegrationDetails, IntegrationKey

from hi.services.frigate.frigate_controller import FrigateController
from hi.services.frigate.frigate_manager import FrigateManager
from hi.services.frigate.frigate_metadata import FrigateMetaData

logging.disable( logging.CRITICAL )


class TestFrigateControllerDoControl( TestCase ):

    def setUp(self):
        self.controller = FrigateController()
        self.mock_manager = Mock( spec = FrigateManager )
        self.controller._frigate_manager = self.mock_manager

    def _detect_details( self, camera_name : str ) -> IntegrationDetails:
        return IntegrationDetails(
            key = IntegrationKey(
                integration_id = FrigateMetaData.integration_id,
                integration_name = (
                    f'{FrigateManager.DETECT_CONTROLLER_PREFIX}.{camera_name}'
                ),
            ),
        )

    def test_on_value_translates_to_frigate_enabled_true(self):
        result = self.controller.do_control(
            integration_details = self._detect_details( 'front_yard' ),
            hi_control_value = 'on',
        )
        self.mock_manager.set_camera_detect.assert_called_once_with(
            camera_name = 'front_yard', enabled = 'true',
        )
        self.assertEqual( result.new_value, 'on' )
        self.assertEqual( result.error_list, [] )

    def test_off_value_translates_to_frigate_enabled_false(self):
        result = self.controller.do_control(
            integration_details = self._detect_details( 'driveway' ),
            hi_control_value = 'off',
        )
        self.mock_manager.set_camera_detect.assert_called_once_with(
            camera_name = 'driveway', enabled = 'false',
        )
        self.assertEqual( result.new_value, 'off' )

    def test_unknown_hi_value_returns_error_without_calling_manager(self):
        result = self.controller.do_control(
            integration_details = self._detect_details( 'front_yard' ),
            hi_control_value = 'maybe',
        )
        self.mock_manager.set_camera_detect.assert_not_called()
        self.assertIsNone( result.new_value )
        self.assertEqual( len( result.error_list ), 1 )

    def test_unknown_integration_name_returns_error(self):
        details = IntegrationDetails(
            key = IntegrationKey(
                integration_id = FrigateMetaData.integration_id,
                integration_name = 'unknown.shape',
            ),
        )
        result = self.controller.do_control(
            integration_details = details,
            hi_control_value = 'on',
        )
        self.mock_manager.set_camera_detect.assert_not_called()
        self.assertIsNone( result.new_value )
        self.assertEqual( len( result.error_list ), 1 )

    def test_manager_exception_surfaces_as_error(self):
        self.mock_manager.set_camera_detect.side_effect = RuntimeError(
            'Frigate client not available.',
        )
        result = self.controller.do_control(
            integration_details = self._detect_details( 'front_yard' ),
            hi_control_value = 'on',
        )
        self.assertIsNone( result.new_value )
        self.assertEqual( len( result.error_list ), 1 )
        self.assertIn( 'Frigate client not available', result.error_list[0] )
