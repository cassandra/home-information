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
                
            response = self.hass_manager().hass_client.set_state(
                entity_id = entity_id,
                state = hass_state_value,
            )

            if response.status_code == 200:
                error_list = list()
            else:
                error_list = [ f'Bad HAss response. Status code = {response.status_code}' ]
            
            logger.debug( f'HAss set state: {entity_id}={hass_state_value}, response={response}' )
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
