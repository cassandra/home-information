import logging

from hi.integrations.connect.integration_controller import IntegrationController
from hi.integrations.transient_models import IntegrationDetails
from hi.integrations.transient_models import IntegrationControlResult

from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassController( IntegrationController, HassMixin ):

    def do_control( self,
                    integration_details : IntegrationDetails,
                    hi_control_value    : str             ) -> IntegrationControlResult:
        logger.debug( f'HAss do_control ENTRY: integration_details={integration_details},'
                      f' hi_control_value={hi_control_value}' )
        try:
            hass_substate_id = integration_details.key.integration_name
            domain_payload = integration_details.payload or {}
            service_call = HassConverter.hi_value_to_hass_service_call(
                hass_substate_id = hass_substate_id,
                hi_control_value = hi_control_value,
                domain_payload = domain_payload,
            )
            self.hass_manager().hass_client.call_service(
                domain = service_call.domain,
                service = service_call.service,
                hass_entity_id = service_call.hass_entity_id,
                service_data = service_call.service_data,
            )
            return IntegrationControlResult(
                new_value = hi_control_value,
                error_list = [],
            )
        except Exception as e:
            logger.warning( f'Exception in HAss do_control: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ str(e) ],
            )

    def _do_control_with_set_state( self,
                                    hass_entity_id      : str,
                                    hi_control_value    : str,
                                    hass_substate_value : str ) -> IntegrationControlResult:
        """
        Legacy method using Home Assistant set_state API. Retained for
        debugging and special use cases; not invoked by the live
        ``do_control`` path which uses HA service calls instead.
        """
        logger.debug( f'HAss attempting set state: {hass_entity_id}={hass_substate_value}' )

        response_data = self.hass_manager().hass_client.set_state(
            entity_id = hass_entity_id,
            state = hass_substate_value,
        )

        error_list = list()
        logger.debug( f'HAss set state SUCCESS: {hass_entity_id}={hass_substate_value},'
                      f' response_data={response_data}' )
        return IntegrationControlResult(
            new_value = hi_control_value,
            error_list = error_list,
        )
