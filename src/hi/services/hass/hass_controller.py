import logging

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_key import IntegrationKey
from hi.integrations.transient_models import IntegrationControlResult

from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassController( IntegrationController, HassMixin ):

    # Use service calls for device control (recommended approach)
    # Set to False to fall back to set_state API for debugging/special cases
    USE_SERVICE_CALLS = True

    def do_control( self,
                    integration_key  : IntegrationKey,
                    control_value    : str             ) -> IntegrationControlResult:
        logger.debug( f'HAss do_control ENTRY: integration_key={integration_key}, control_value={control_value}' )
        try:
            entity_id = integration_key.integration_name
            logger.debug( f'HAss do_control entity_id: {entity_id}' )
            
            hass_state_value = HassConverter.hass_entity_id_to_state_value_str(
                hass_entity_id = entity_id,
                hi_value = control_value,
            )
            logger.debug( f'HAss do_control converted value: {hass_state_value}' )
                
            if self.USE_SERVICE_CALLS:
                return self._do_control_with_services( entity_id, control_value, hass_state_value )
            else:
                return self._do_control_with_set_state( entity_id, control_value, hass_state_value )
        except Exception as e:
            logger.warning( f'Exception in HAss do_control: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ str(e) ],
            )

    def _do_control_with_set_state( self, hass_state_id: str, control_value: str, hass_state_value: str ) -> IntegrationControlResult:
        """
        Legacy method using Home Assistant set_state API.
        
        Note: This method updates HA's internal state but may not actually
        control physical devices. Kept for debugging and special use cases.
        """
        logger.debug( f'HAss attempting set state: {hass_state_id}={hass_state_value}' )
        
        response_data = self.hass_manager().hass_client.set_state(
            entity_id = hass_state_id,
            state = hass_state_value,
        )

        # If we get here, the HTTP call succeeded (set_state raises exception on failure)
        error_list = list()
        logger.debug( f'HAss set state SUCCESS: {hass_state_id}={hass_state_value}, response_data={response_data}' )
        return IntegrationControlResult(
            new_value = control_value,
            error_list = error_list,
        )

    def _do_control_with_services( self, hass_state_id: str, control_value: str, hass_state_value: str ) -> IntegrationControlResult:
        """Use Home Assistant service calls for device control (recommended approach)"""
        
        # Parse domain from hass_state_id (e.g., 'light' from 'light.switch_name')
        if '.' not in hass_state_id:
            logger.warning( f'Invalid hass_state_id format: {hass_state_id}' )
            return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
        
        domain = hass_state_id.split('.', 1)[0]
        
        # Handle controllable devices with services
        if domain in ['light', 'switch']:
            return self._control_on_off_device( domain, hass_state_id, control_value, hass_state_value )
        
        # For all other domains, fall back to original set_state method
        else:
            logger.debug( f'HAss using set_state fallback for domain: {domain}' )
            return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )

    def _control_on_off_device( self, domain: str, hass_state_id: str, control_value: str, hass_state_value: str ) -> IntegrationControlResult:
        """Handle on/off control for lights, switches, and similar devices"""
        logger.debug( f'HAss attempting service call for {domain}: {hass_state_id}={control_value}' )
        
        # Determine service based on control value
        if control_value.lower() in ['on', 'true', '1']:
            service = 'turn_on'
        elif control_value.lower() in ['off', 'false', '0']:
            service = 'turn_off'
        else:
            logger.warning( f'Unknown {domain} control value "{control_value}", falling back to set_state' )
            return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
        
        # Call the Home Assistant service
        response = self.hass_manager().hass_client.call_service(
            domain = domain,
            service = service,
            hass_state_id = hass_state_id,
        )
        
        error_list = list()
        logger.debug( f'HAss service call SUCCESS: {domain}.{service} for {hass_state_id}' )
        return IntegrationControlResult(
            new_value = control_value,
            error_list = error_list,
        )
