import logging

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_key import IntegrationKey
from hi.integrations.transient_models import IntegrationControlResult

from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassController( IntegrationController, HassMixin ):

    def do_control( self,
                    integration_key  : IntegrationKey,
                    control_value    : str             ) -> IntegrationControlResult:
        try:
            entity_id = integration_key.integration_name
            hass_state_value = HassConverter.hass_entity_id_to_state_value_str(
                hass_entity_id = entity_id,
                hi_value = control_value,
            )
                
            logger.debug( f'HAss attempting set state: {entity_id}={hass_state_value}' )
            
            response_data = self.hass_manager().hass_client.set_state(
                entity_id = entity_id,
                state = hass_state_value,
            )

            # If we get here, the HTTP call succeeded (set_state raises exception on failure)
            error_list = list()
            logger.debug( f'HAss set state SUCCESS: {entity_id}={hass_state_value}, response_data={response_data}' )
            return IntegrationControlResult(
                new_value = control_value,
                error_list = error_list,
            )

        except Exception as e:
            logger.warning( f'Exception in HAss do_control: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ str(e) ],
            )
