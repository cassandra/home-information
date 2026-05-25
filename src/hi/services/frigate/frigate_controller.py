import logging

from hi.integrations.connector.integration_controller import IntegrationController
from hi.integrations.transient_models import (
    IntegrationControlResult,
    IntegrationDetails,
)

from .frigate_mixins import FrigateMixin

logger = logging.getLogger(__name__)


class FrigateController( IntegrationController, FrigateMixin ):
    """Routes HI control commands to Frigate.

    v1 has no exposed control surface. Frigate's only operator-toggle
    reachable over HTTP — ``PUT /api/config/set`` for
    ``cameras.<name>.detect.enabled`` — is a config edit rather than
    transient state, with persistence semantics that don't map
    cleanly to HI's control model. A future revision can expose the
    transient detect toggle through Frigate's MQTT
    ``frigate/<cam>/detect/set`` topic instead.
    """

    def do_control(
            self,
            integration_details : IntegrationDetails,
            hi_control_value    : str,
    ) -> IntegrationControlResult:
        integration_key = integration_details.key
        message = (
            f'No Frigate control mapping for integration_name '
            f'{integration_key.integration_name!r}.'
        )
        logger.warning( message )
        return IntegrationControlResult(
            new_value = None,
            error_list = [ message ],
        )
