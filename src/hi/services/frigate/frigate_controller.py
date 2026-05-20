import logging

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.transient_models import (
    IntegrationControlResult,
    IntegrationDetails,
)

from .frigate_mixins import FrigateMixin

logger = logging.getLogger(__name__)


class FrigateController( IntegrationController, FrigateMixin ):
    """Routes HI control commands to Frigate API calls.

    v1 control surface (added in feature work):
    - Per-camera Detect On/Off controller → ``camera.enable_detection``
      / ``camera.disable_detection`` (or the relevant Frigate API
      endpoint).

    Scaffolding stub: returns "not yet implemented" for every action.
    """

    def do_control(
            self,
            integration_details : IntegrationDetails,
            hi_control_value    : str,
    ) -> IntegrationControlResult:
        integration_key = integration_details.key
        logger.warning(
            f'Frigate control not yet implemented (scaffolding):'
            f' key={integration_key} value={hi_control_value}'
        )
        return IntegrationControlResult(
            new_value = None,
            error_list = [ 'Frigate control not yet implemented (scaffolding).' ],
        )
