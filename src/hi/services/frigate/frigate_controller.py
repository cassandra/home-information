import logging

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.transient_models import (
    IntegrationControlResult,
    IntegrationDetails,
)

from .frigate_converter import FrigateConverter
from .frigate_manager import FrigateManager
from .frigate_mixins import FrigateMixin

logger = logging.getLogger(__name__)


class FrigateController( IntegrationController, FrigateMixin ):
    """Routes HI control commands to Frigate API calls.

    v1 control surface:
      Per-camera Detect On/Off — integration_name shape
      ``<DETECT_CONTROLLER_PREFIX>.<camera_name>``.
    """

    def do_control(
            self,
            integration_details : IntegrationDetails,
            hi_control_value    : str,
    ) -> IntegrationControlResult:
        integration_key = integration_details.key
        integration_name = integration_key.integration_name or ''

        detect_prefix = FrigateManager.DETECT_CONTROLLER_PREFIX + '.'
        if integration_name.startswith( detect_prefix ):
            camera_name = integration_name[ len( detect_prefix ): ]
            return self._do_detect_control(
                camera_name = camera_name,
                hi_control_value = hi_control_value,
            )

        message = f'No Frigate control mapping for integration_name {integration_name!r}.'
        logger.warning( message )
        return IntegrationControlResult(
            new_value = None,
            error_list = [ message ],
        )

    def _do_detect_control(
            self,
            camera_name      : str,
            hi_control_value : str,
    ) -> IntegrationControlResult:
        if not camera_name:
            message = 'Frigate detect controller missing camera_name in integration key.'
            logger.warning( message )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ message ],
            )
        detect_enabled = FrigateConverter.hi_control_to_detect_enabled(
            hi_control_value = hi_control_value,
        )
        if detect_enabled is None:
            message = (
                f'Unsupported HI control value for Frigate detect: '
                f'{hi_control_value!r}.'
            )
            logger.warning( message )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ message ],
            )
        try:
            self.frigate_manager().set_camera_detect(
                camera_name = camera_name,
                enabled = detect_enabled,
            )
        except Exception as e:
            logger.warning( f'Frigate detect control failed: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ str( e ) ],
            )
        return IntegrationControlResult(
            new_value = hi_control_value,
            error_list = [],
        )
