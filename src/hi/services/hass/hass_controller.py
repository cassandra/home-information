import logging

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.transient_models import IntegrationDetails
from hi.integrations.transient_models import IntegrationControlResult

from .hass_converter import HassConverter
from .hass_mixins import HassMixin

logger = logging.getLogger(__name__)


class HassController( IntegrationController, HassMixin ):

    def do_control( self,
                    integration_details : IntegrationDetails,
                    control_value       : str             ) -> IntegrationControlResult:
        logger.debug( f'HAss do_control ENTRY: integration_details={integration_details},'
                      f' control_value={control_value}' )
        try:
            entity_id = integration_details.key.integration_name
            domain_payload = integration_details.payload or {}
            logger.debug( f'HAss do_control entity_id: {entity_id}, payload: {domain_payload}' )
            
            hass_state_value = HassConverter.hass_entity_id_to_state_value_str(
                hass_entity_id = entity_id,
                hi_value = control_value,
            )
            logger.debug( f'HAss do_control converted value: {hass_state_value}' )
                
            return self._do_control_with_services( entity_id,
                                                   control_value,
                                                   hass_state_value,
                                                   domain_payload )
        except Exception as e:
            logger.warning( f'Exception in HAss do_control: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [ str(e) ],
            )

    def _do_control_with_set_state( self,
                                    hass_state_id     : str,
                                    control_value     : str,
                                    hass_state_value  : str ) -> IntegrationControlResult:
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
        logger.debug( f'HAss set state SUCCESS: {hass_state_id}={hass_state_value},'
                      f' response_data={response_data}' )
        return IntegrationControlResult(
            new_value = control_value,
            error_list = error_list,
        )

    def _do_control_with_services( self,
                                   hass_state_id    : str,
                                   control_value    : str,
                                   hass_state_value : str,
                                   domain_payload   : dict ) -> IntegrationControlResult:
        """Use Home Assistant service calls for device control (recommended approach)"""
        
        # Extract domain from payload (more reliable than parsing entity_id)
        domain = domain_payload.get('domain')
        if not domain:
            # Fallback to parsing from entity_id if payload missing
            if '.' not in hass_state_id:
                logger.warning( f'Invalid hass_state_id format and no domain payload:'
                                f' {hass_state_id}' )
                return IntegrationControlResult(
                    new_value = None,
                    error_list = [f'Invalid entity_id format: {hass_state_id}'],
                )
            domain = hass_state_id.split('.', 1)[0]
            logger.warning( f'Missing domain payload for {hass_state_id},'
                            f' using parsed domain: {domain}' )
        
        # Use payload-based service routing if available, otherwise best-effort
        if domain_payload:
            return self._control_device_with_payload( domain,
                                                      hass_state_id,
                                                      control_value,
                                                      hass_state_value,
                                                      domain_payload )
        else:
            return self._control_device_best_effort( domain,
                                                     hass_state_id,
                                                     control_value,
                                                     hass_state_value )

    def _control_on_off_device( self,
                                domain: str,
                                hass_state_id: str,
                                control_value: str,
                                hass_state_value: str ) -> IntegrationControlResult:
        """Handle on/off control for lights, switches, and similar devices"""
        logger.debug( f'HAss attempting service call for {domain}:'
                      f' {hass_state_id}={control_value}' )
        
        # Determine service based on control value
        if control_value.lower() in ['on', 'true', '1']:
            service = 'turn_on'
        elif control_value.lower() in ['off', 'false', '0']:
            service = 'turn_off'
        else:
            logger.warning( f'Unknown {domain} control value "{control_value}"' )
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
        
        error_list = list()
        logger.debug( f'HAss service call SUCCESS: {domain}.{service} for {hass_state_id}' )
        return IntegrationControlResult(
            new_value = control_value,
            error_list = error_list,
        )

    def _control_device_best_effort( self,
                                     domain            : str,
                                     hass_state_id     : str,
                                     control_value     : str,
                                     hass_state_value  : str ) -> IntegrationControlResult:
        """
        Best-effort device control when payload is missing.
        Uses standard Home Assistant service patterns based on domain and control value.
        """
        logger.debug( f'HAss best-effort control: {domain} {hass_state_id}={control_value}' )
        
        try:
            # Handle numeric controls for known domains
            if self._is_numeric_value( control_value ):
                return self._control_numeric_best_effort( domain, hass_state_id, control_value )
            
            # Handle on/off/open/close controls
            return self._control_on_off_best_effort( domain, hass_state_id, control_value )
            
        except Exception as e:
            logger.warning( f'Best-effort control failed for {hass_state_id}: {e}' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Best-effort control failed: {str(e)}'],
            )

    def _is_numeric_value( self, control_value: str ) -> bool:
        """Check if control value is numeric"""
        try:
            float(control_value)
            return True
        except (ValueError, TypeError):
            return False

    def _control_on_off_best_effort( self,
                                     domain         : str,
                                     hass_state_id  : str,
                                     control_value  : str ) -> IntegrationControlResult:
        """Best-effort on/off/open/close control based on standard HA patterns"""
        logger.debug( f'HAss best-effort on/off control: {domain} {hass_state_id}={control_value}' )
        
        # Determine service based on control value and domain
        control_lower = control_value.lower()
        
        if control_lower in ['on', 'true', '1']:
            service = 'turn_on'
        elif control_lower in ['off', 'false', '0']:
            service = 'turn_off'
        elif control_lower in ['open']:
            if domain == 'cover':
                service = 'open_cover'
            elif domain == 'lock':
                service = 'unlock'
            else:
                service = 'turn_on'  # Fallback
        elif control_lower in ['close']:
            if domain == 'cover':
                service = 'close_cover'
            elif domain == 'lock':
                service = 'lock'
            else:
                service = 'turn_off'  # Fallback
        else:
            logger.warning( f'Unknown control value "{control_value}"'
                            f' for best-effort control of {hass_state_id}' )
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
        
        logger.debug( f'HAss best-effort service call SUCCESS: {domain}.{service}'
                      f' for {hass_state_id}' )
        return IntegrationControlResult(
            new_value = control_value,
            error_list = [],
        )

    def _control_numeric_best_effort( self,
                                      domain         : str,
                                      hass_state_id  : str,
                                      control_value  : str ) -> IntegrationControlResult:
        """Best-effort numeric control based on common HA patterns"""
        logger.debug( f'HAss best-effort numeric control: {domain}'
                      f' {hass_state_id}={control_value}' )
        
        try:
            numeric_value = float(control_value)
            
            # Light brightness (0-100%)
            if domain == 'light':
                brightness_pct = int(numeric_value)
                if not (0 <= brightness_pct <= 100):
                    return IntegrationControlResult(
                        new_value = None,
                        error_list = [f'Invalid brightness value: {brightness_pct} (must be 0-100)'],
                    )
                
                if brightness_pct == 0:
                    service = 'turn_off'
                    service_data = None
                else:
                    service = 'turn_on'
                    service_data = {'brightness_pct': brightness_pct}
                
                self.hass_manager().hass_client.call_service(
                    domain = domain,
                    service = service,
                    hass_state_id = hass_state_id,
                    service_data = service_data,
                )
                
                logger.debug( f'HAss best-effort light control SUCCESS: {domain}.{service} for {hass_state_id}' )
                return IntegrationControlResult(
                    new_value = str(brightness_pct),
                    error_list = [],
                )
            
            # Climate temperature
            elif domain == 'climate':
                self.hass_manager().hass_client.call_service(
                    domain = domain,
                    service = 'set_temperature',
                    hass_state_id = hass_state_id,
                    service_data = {'temperature': numeric_value},
                )
                
                logger.debug( f'HAss best-effort climate control SUCCESS: climate.set_temperature for {hass_state_id}' )
                return IntegrationControlResult(
                    new_value = str(numeric_value),
                    error_list = [],
                )
            
            # Cover position (0-100%)
            elif domain == 'cover':
                position_pct = int(numeric_value)
                if not (0 <= position_pct <= 100):
                    return IntegrationControlResult(
                        new_value = None,
                        error_list = [f'Invalid position value: {position_pct} (must be 0-100)'],
                    )
                
                self.hass_manager().hass_client.call_service(
                    domain = domain,
                    service = 'set_cover_position',
                    hass_state_id = hass_state_id,
                    service_data = {'position': position_pct},
                )
                
                logger.debug( f'HAss best-effort cover control SUCCESS: cover.set_cover_position for {hass_state_id}' )
                return IntegrationControlResult(
                    new_value = str(position_pct),
                    error_list = [],
                )
            
            # Media player volume (0.0-1.0)
            elif domain == 'media_player':
                if not (0.0 <= numeric_value <= 1.0):
                    return IntegrationControlResult(
                        new_value = None,
                        error_list = [f'Invalid volume value: {numeric_value} (must be 0.0-1.0)'],
                    )
                
                self.hass_manager().hass_client.call_service(
                    domain = domain,
                    service = 'volume_set',
                    hass_state_id = hass_state_id,
                    service_data = {'volume_level': numeric_value},
                )
                
                logger.debug( f'HAss best-effort media_player control SUCCESS: media_player.volume_set for {hass_state_id}' )
                return IntegrationControlResult(
                    new_value = str(numeric_value),
                    error_list = [],
                )
            
            # Other domains - try generic approach
            else:
                logger.warning( f'No best-effort numeric control pattern for domain {domain}, entity {hass_state_id}' )
                return IntegrationControlResult(
                    new_value = None,
                    error_list = [f'No numeric control pattern for domain: {domain}'],
                )
                
        except ValueError:
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Invalid numeric value: {control_value}'],
            )
    
    def _control_device_with_payload( self, domain: str, hass_state_id: str, control_value: str, hass_state_value: str, domain_payload: dict ) -> IntegrationControlResult:
        """Use stored payload to control device directly"""
        logger.debug( f'HAss payload-based control: {domain} {hass_state_id}={control_value}, payload={domain_payload}' )
        
        # Check if device is controllable
        if not domain_payload.get('is_controllable', False):
            logger.warning( f'Device {hass_state_id} is not controllable, attempting best-effort control' )
            return self._control_device_best_effort( domain, hass_state_id, control_value, hass_state_value )
        
        # Handle complex numeric controls (brightness, temperature, volume, etc.)
        if self._is_numeric_control( control_value, domain_payload ):
            return self._control_numeric_parameter_device( domain, hass_state_id, control_value, domain_payload )
        
        # Handle on/off control
        if control_value.lower() in ['on', 'true', '1']:
            service = domain_payload.get('on_service')
            if not service:
                logger.warning( f'No on_service defined in payload for {hass_state_id}, using best-effort control' )
                return self._control_device_best_effort( domain, hass_state_id, control_value, hass_state_value )
        elif control_value.lower() in ['off', 'false', '0']:
            service = domain_payload.get('off_service')
            if not service:
                logger.warning( f'No off_service defined in payload for {hass_state_id}, using best-effort control' )
                return self._control_device_best_effort( domain, hass_state_id, control_value, hass_state_value )
        elif control_value.lower() in ['open']:
            service = domain_payload.get('open_service')
            if not service:
                logger.warning( f'No open_service defined in payload for {hass_state_id}, using best-effort control' )
                return self._control_device_best_effort( domain, hass_state_id, control_value, hass_state_value )
        elif control_value.lower() in ['close']:
            service = domain_payload.get('close_service')
            if not service:
                logger.warning( f'No close_service defined in payload for {hass_state_id}, using best-effort control' )
                return self._control_device_best_effort( domain, hass_state_id, control_value, hass_state_value )
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
    
    def _is_numeric_control( self, control_value: str, domain_payload: dict ) -> bool:
        """Check if control value should be handled as numeric parameter"""
        try:
            # Must be a valid numeric value
            float(control_value)
            
            # Must have either brightness support or set_service for numeric parameters  
            return ( domain_payload.get('supports_brightness', False)
                     or domain_payload.get('set_service') is not None )
        except (ValueError, TypeError):
            return False
    
    def _control_numeric_parameter_device( self,
                                           domain          : str,
                                           hass_state_id   : str,
                                           control_value   : str,
                                           domain_payload : dict ) -> IntegrationControlResult:
        """Handle numeric parameter controls (brightness, temperature, volume, position, etc.)"""
        try:
            numeric_value = float(control_value)
            
            # Handle brightness control (0-100%)
            if domain_payload.get('supports_brightness', False):
                return self._control_brightness_value( domain, hass_state_id, numeric_value, domain_payload )
            
            # Handle temperature control  
            elif 'temperature' in domain_payload.get('parameters', {}):
                return self._control_temperature_value( domain, hass_state_id, numeric_value, domain_payload )
            
            # Handle volume control
            elif 'volume_level' in domain_payload.get('parameters', {}):
                return self._control_volume_value( domain, hass_state_id, numeric_value, domain_payload )
            
            # Handle position control (covers, etc.)
            elif 'position' in domain_payload.get('parameters', {}):
                return self._control_position_value( domain, hass_state_id, numeric_value, domain_payload )
            
            # Generic set_service fallback
            elif domain_payload.get('set_service'):
                service = domain_payload.get('set_service')
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
    
    def _control_brightness_value( self, domain: str, hass_state_id: str, brightness: float, domain_payload: dict ) -> IntegrationControlResult:
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
            service = domain_payload.get('off_service')
            service_data = None
        else:
            # Turn on with brightness
            service = domain_payload.get('on_service') 
            service_data = {'brightness_pct': brightness_pct}
        
        if not service:
            logger.warning( f'No appropriate service defined in payload for brightness control of {hass_state_id}' )
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
    
    def _control_temperature_value( self, domain: str, hass_state_id: str, temperature: float, domain_payload: dict ) -> IntegrationControlResult:
        """Handle temperature control for thermostats"""
        service = domain_payload.get('set_service')
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
    
    def _control_volume_value( self, domain: str, hass_state_id: str, volume: float, domain_payload: dict ) -> IntegrationControlResult:
        """Handle volume control for media players (0.0-1.0)"""
        if not (0.0 <= volume <= 1.0):
            logger.warning( f'Invalid volume value {volume} for {hass_state_id} (must be 0.0-1.0)' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Invalid volume value: {volume} (must be 0.0-1.0)'],
            )
        
        service = domain_payload.get('set_service', 'volume_set')
        
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
    
    def _control_position_value( self, domain: str, hass_state_id: str, position: float, domain_payload: dict ) -> IntegrationControlResult:
        """Handle position control for covers (0-100%)"""
        position_pct = int(position)
        if not (0 <= position_pct <= 100):
            logger.warning( f'Invalid position value {position} for {hass_state_id} (must be 0-100)' )
            return IntegrationControlResult(
                new_value = None,
                error_list = [f'Invalid position value: {position} (must be 0-100)'],
            )
        
        service = domain_payload.get('set_service', 'set_cover_position')
        
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
