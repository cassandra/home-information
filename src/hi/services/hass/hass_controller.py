import logging

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_key import IntegrationData
from hi.integrations.transient_models import IntegrationControlResult

from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassController( IntegrationController, HassMixin ):

    # Use service calls for device control (recommended approach)
    # Set to False to fall back to set_state API for debugging/special cases
    USE_SERVICE_CALLS = True

    def do_control( self,
                    integration_data : IntegrationData,
                    control_value    : str             ) -> IntegrationControlResult:
        logger.debug( f'HAss do_control ENTRY: integration_data={integration_data}, control_value={control_value}' )
        try:
            entity_id = integration_data.key.integration_name
            domain_metadata = integration_data.metadata or {}
            logger.debug( f'HAss do_control entity_id: {entity_id}, metadata: {domain_metadata}' )
            
            hass_state_value = HassConverter.hass_entity_id_to_state_value_str(
                hass_entity_id = entity_id,
                hi_value = control_value,
            )
            logger.debug( f'HAss do_control converted value: {hass_state_value}' )
                
            if self.USE_SERVICE_CALLS:
                return self._do_control_with_services( entity_id, control_value, hass_state_value, domain_metadata )
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

    def _do_control_with_services( self, hass_state_id: str, control_value: str, hass_state_value: str, domain_metadata: dict ) -> IntegrationControlResult:
        """Use Home Assistant service calls for device control (recommended approach)"""
        
        # Extract domain from metadata (more reliable than parsing entity_id)
        domain = domain_metadata.get('domain')
        if not domain:
            # Fallback to parsing from entity_id if metadata missing
            if '.' not in hass_state_id:
                logger.warning( f'Invalid hass_state_id format and no domain metadata: {hass_state_id}' )
                return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
            domain = hass_state_id.split('.', 1)[0]
            logger.warning( f'Missing domain metadata for {hass_state_id}, using parsed domain: {domain}' )
        
        # Use metadata-based service routing
        return self._control_device_with_metadata( domain, hass_state_id, control_value, hass_state_value, domain_metadata )

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
        self.hass_manager().hass_client.call_service(
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
    
    def _control_device_with_metadata( self, domain: str, hass_state_id: str, control_value: str, hass_state_value: str, domain_metadata: dict ) -> IntegrationControlResult:
        """Use stored metadata to control device directly"""
        logger.debug( f'HAss metadata-based control: {domain} {hass_state_id}={control_value}, metadata={domain_metadata}' )
        
        # Check if device is controllable
        if not domain_metadata.get('is_controllable', False):
            logger.warning( f'Device {hass_state_id} is not controllable, falling back to set_state' )
            return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
        
        # Handle complex numeric controls (brightness, temperature, volume, etc.)
        if self._is_numeric_control( control_value, domain_metadata ):
            return self._control_numeric_parameter_device( domain, hass_state_id, control_value, domain_metadata )
        
        # Handle on/off control
        if control_value.lower() in ['on', 'true', '1']:
            service = domain_metadata.get('on_service')
            if not service:
                logger.warning( f'No on_service defined in metadata for {hass_state_id}' )
                return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
        elif control_value.lower() in ['off', 'false', '0']:
            service = domain_metadata.get('off_service')
            if not service:
                logger.warning( f'No off_service defined in metadata for {hass_state_id}' )
                return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
        elif control_value.lower() in ['open']:
            service = domain_metadata.get('open_service')
            if not service:
                logger.warning( f'No open_service defined in metadata for {hass_state_id}' )
                return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
        elif control_value.lower() in ['close']:
            service = domain_metadata.get('close_service')
            if not service:
                logger.warning( f'No close_service defined in metadata for {hass_state_id}' )
                return self._do_control_with_set_state( hass_state_id, control_value, hass_state_value )
        else:
            logger.warning( f'Unknown control value "{control_value}" for {hass_state_id}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Unknown control value: {control_value}'],
            )
        
        # Call the Home Assistant service
        self.hass_manager().hass_client.call_service(
            domain = domain,
            service = service,
            hass_state_id = hass_state_id,
        )
        
        logger.debug( f'HAss service call SUCCESS: {domain}.{service} for {hass_state_id}' )
        return IntegrationControlResult(
            new_value = control_value,
            error_list = [],
        )
    
    def _is_numeric_control( self, control_value: str, domain_metadata: dict ) -> bool:
        """Check if control value should be handled as numeric parameter"""
        try:
            # Must be a valid numeric value
            float(control_value)
            
            # Must have either brightness support or set_service for numeric parameters  
            return (domain_metadata.get('supports_brightness', False) or
                    domain_metadata.get('set_service') is not None)
        except (ValueError, TypeError):
            return False
    
    def _control_numeric_parameter_device( self, domain: str, hass_state_id: str, control_value: str, domain_metadata: dict ) -> IntegrationControlResult:
        """Handle numeric parameter controls (brightness, temperature, volume, position, etc.)"""
        try:
            numeric_value = float(control_value)
            
            # Handle brightness control (0-100%)
            if domain_metadata.get('supports_brightness', False):
                return self._control_brightness_value( domain, hass_state_id, numeric_value, domain_metadata )
            
            # Handle temperature control  
            elif 'temperature' in domain_metadata.get('parameters', {}):
                return self._control_temperature_value( domain, hass_state_id, numeric_value, domain_metadata )
            
            # Handle volume control
            elif 'volume_level' in domain_metadata.get('parameters', {}):
                return self._control_volume_value( domain, hass_state_id, numeric_value, domain_metadata )
            
            # Handle position control (covers, etc.)
            elif 'position' in domain_metadata.get('parameters', {}):
                return self._control_position_value( domain, hass_state_id, numeric_value, domain_metadata )
            
            # Generic set_service fallback
            elif domain_metadata.get('set_service'):
                service = domain_metadata.get('set_service')
                # Use the numeric value directly - service will determine parameter name
                service_data = {domain.rstrip('s'): numeric_value}  # e.g., climate -> temperature
                
                self.hass_manager().hass_client.call_service(
                    domain = domain,
                    service = service,
                    hass_state_id = hass_state_id,
                    service_data = service_data,
                )
                
                logger.debug( f'HAss numeric control SUCCESS: {domain}.{service} for {hass_state_id} value={numeric_value}' )
                return IntegrationControlResult(
                    new_value = control_value,
                    error_list = [],
                )
            
            else:
                logger.warning( f'No numeric parameter handling defined for {hass_state_id}' )
                return IntegrationControlResult(
                    new_value = None,
                    error_list = ['No numeric parameter handling defined'],
                )
                
        except ValueError:
            logger.warning( f'Invalid numeric control value: {control_value}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Invalid numeric value: {control_value}'],
            )
    
    def _control_brightness_value( self, domain: str, hass_state_id: str, brightness: float, domain_metadata: dict ) -> IntegrationControlResult:
        """Handle brightness/dimmer control (0-100%)"""
        brightness_pct = int(brightness)
        if not (0 <= brightness_pct <= 100):
            logger.warning( f'Invalid brightness value {brightness} for {hass_state_id}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Invalid brightness value: {brightness}'],
            )
        
        if brightness_pct == 0:
            # Turn off for 0% brightness
            service = domain_metadata.get('off_service')
            service_data = None
        else:
            # Turn on with brightness
            service = domain_metadata.get('on_service') 
            service_data = {'brightness_pct': brightness_pct}
        
        if not service:
            logger.warning( f'No appropriate service defined in metadata for brightness control of {hass_state_id}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = ['No service defined for brightness control'],
            )
        
        # Call the Home Assistant service
        self.hass_manager().hass_client.call_service(
            domain = domain,
            service = service,
            hass_state_id = hass_state_id,
            service_data = service_data,
        )
        
        logger.debug( f'HAss brightness control SUCCESS: {domain}.{service} for {hass_state_id} brightness={brightness_pct}%' )
        return IntegrationControlResult(
            new_value = str(brightness_pct),
            error_list = [],
        )
    
    def _control_temperature_value( self, domain: str, hass_state_id: str, temperature: float, domain_metadata: dict ) -> IntegrationControlResult:
        """Handle temperature control for thermostats"""
        service = domain_metadata.get('set_service')
        if not service:
            logger.warning( f'No set_service defined for temperature control of {hass_state_id}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = ['No temperature service defined'],
            )
        
        # Call the Home Assistant service
        self.hass_manager().hass_client.call_service(
            domain = domain,
            service = service,
            hass_state_id = hass_state_id,
            service_data = {'temperature': temperature},
        )
        
        logger.debug( f'HAss temperature control SUCCESS: {domain}.{service} for {hass_state_id} temperature={temperature}' )
        return IntegrationControlResult(
            new_value = str(temperature),
            error_list = [],
        )
    
    def _control_volume_value( self, domain: str, hass_state_id: str, volume: float, domain_metadata: dict ) -> IntegrationControlResult:
        """Handle volume control for media players (0.0-1.0)"""
        if not (0.0 <= volume <= 1.0):
            logger.warning( f'Invalid volume value {volume} for {hass_state_id} (must be 0.0-1.0)' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Invalid volume value: {volume} (must be 0.0-1.0)'],
            )
        
        service = domain_metadata.get('set_service', 'volume_set')
        
        # Call the Home Assistant service
        self.hass_manager().hass_client.call_service(
            domain = domain,
            service = service,
            hass_state_id = hass_state_id,
            service_data = {'volume_level': volume},
        )
        
        logger.debug( f'HAss volume control SUCCESS: {domain}.{service} for {hass_state_id} volume={volume}' )
        return IntegrationControlResult(
            new_value = str(volume),
            error_list = [],
        )
    
    def _control_position_value( self, domain: str, hass_state_id: str, position: float, domain_metadata: dict ) -> IntegrationControlResult:
        """Handle position control for covers (0-100%)"""
        position_pct = int(position)
        if not (0 <= position_pct <= 100):
            logger.warning( f'Invalid position value {position} for {hass_state_id} (must be 0-100)' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Invalid position value: {position} (must be 0-100)'],
            )
        
        service = domain_metadata.get('set_service', 'set_cover_position')
        
        # Call the Home Assistant service
        self.hass_manager().hass_client.call_service(
            domain = domain,
            service = service,
            hass_state_id = hass_state_id,
            service_data = {'position': position_pct},
        )
        
        logger.debug( f'HAss position control SUCCESS: {domain}.{service} for {hass_state_id} position={position_pct}%' )
        return IntegrationControlResult(
            new_value = str(position_pct),
            error_list = [],
        )
