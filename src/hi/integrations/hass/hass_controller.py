import logging

from hi.integrations.core.integration_controller import IntegrationController
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.transient_models import IntegrationControlResult

from .hass_manager import HassManager

logger = logging.getLogger(__name__)


class HassController( IntegrationController ):

    def __init__(self):
        self._hass_manager = HassManager()
        return
    
    def do_control( self,
                    integration_key  : IntegrationKey,
                    control_value    : str             ) -> IntegrationControlResult:
        try:

            entity_id = integration_key.integration_name
            if not control_value:
                control_value = "off"
                
            response = self._hass_manager.hass_client.set_state(
                entity_id = entity_id,
                state = control_value,
            )
            logger.debug( f'HAss set state: {entity_id}={control_value}, response={response}' )
            return IntegrationControlResult(
                new_value = control_value,
                error_list = [],
            )

        except Exception as e:
            logger.warning( f'Exception in HAss do_control: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ str(e) ],
            )
