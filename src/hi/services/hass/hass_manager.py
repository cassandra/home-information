import logging
from asgiref.sync import sync_to_async
from threading import Lock
from typing import Dict, List

import hi.apps.common.datetimeproxy as datetimeproxy
from hi.apps.common.singleton import Singleton
from hi.apps.common.utils import str_to_bool

from hi.integrations.exceptions import IntegrationAttributeError, IntegrationError
from hi.integrations.transient_models import (
    IntegrationKey,
    IntegrationHealthStatus,
    IntegrationHealthStatusType,
)
from hi.integrations.models import Integration, IntegrationAttribute

from .enums import HassAttributeType
from .hass_client import HassClient
from .hass_metadata import HassMetaData
from .hass_models import HassState

logger = logging.getLogger(__name__)


class HassManager( Singleton ):

    def __init_singleton__( self ):
        self._hass_attr_type_to_attribute = dict()
        self._hass_client = None
        
        self._change_listeners = list()
        self._was_initialized = False
        self._data_lock = Lock()
        
        # Health status tracking
        self._health_status = IntegrationHealthStatus(
            status=IntegrationHealthStatusType.UNKNOWN,
            last_check=datetimeproxy.now()
        )
        return

    def ensure_initialized(self):
        if self._was_initialized:
            return
        self.reload()
        self._was_initialized = True
        return
    
    def register_change_listener( self, callback ):
        logger.debug( f'Adding HASS setting change listener from {callback.__module__}' )
        self._change_listeners.append( callback )
        return
    
    def notify_settings_changed(self):
        self.reload()
        for callback in self._change_listeners:
            try:
                callback()
            except Exception:
                logger.exception( 'Problem calling setting change callback.' )
            continue
        return
    
    @property
    def hass_client(self):
        return self._hass_client
    
    def reload( self ):
        """ Called when integration models are changed (via signals below). """
        logger.debug( 'HASS manager loading started.' )
        with self._data_lock:
            try:
                self._hass_attr_type_to_attribute = self._load_attributes()
                self._hass_client = self.create_hass_client( self._hass_attr_type_to_attribute )
                self.clear_caches()
                self._update_health_status(IntegrationHealthStatusType.HEALTHY)
                logger.debug( 'HASS manager loading completed.' )
            except IntegrationError as e:
                error_msg = f'HASS integration configuration error: {e}'
                logger.error(error_msg)
                self._update_health_status(IntegrationHealthStatusType.CONFIG_ERROR, error_msg)
            except IntegrationAttributeError as e:
                error_msg = f'HASS integration attribute error: {e}'
                logger.error(error_msg)
                self._update_health_status(IntegrationHealthStatusType.CONFIG_ERROR, error_msg)
            except Exception as e:
                error_msg = f'Unexpected error loading HASS configuration: {e}'
                logger.exception(error_msg)
                self._update_health_status(IntegrationHealthStatusType.TEMPORARY_ERROR, error_msg)
        return

    def clear_caches(self):
        return

    def _load_attributes(self) -> Dict[ HassAttributeType, IntegrationAttribute ]:
        try:
            hass_integration = Integration.objects.get( integration_id = HassMetaData.integration_id )
        except Integration.DoesNotExist:
            raise IntegrationError( 'Home Assistant integration is not implemented.' )
        
        if not hass_integration.is_enabled:
            raise IntegrationError( 'Home Assistant integration is not enabled.' )
        
        integration_attributes = list(hass_integration.attributes.all())
        return self._build_hass_attr_type_to_attribute_map(
            integration_attributes=integration_attributes,
            enforce_requirements=True
        )
    
    def create_hass_client(
            self,
            hass_attr_type_to_attribute : Dict[ HassAttributeType, IntegrationAttribute ] ) -> HassClient:
        # Verify integration and build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }
        attr_to_api_option_key = {
            HassAttributeType.API_BASE_URL: HassClient.API_BASE_URL,
            HassAttributeType.API_TOKEN: HassClient.API_TOKEN,
        }
        
        integration_key_to_attribute = { x.integration_key: x for x in hass_attr_type_to_attribute.values() }
        for hass_attr_type in attr_to_api_option_key.keys():
            integration_key = IntegrationKey(
                integration_id = HassMetaData.integration_id,
                integration_name = str(hass_attr_type),
            )
            hass_attr = integration_key_to_attribute.get( integration_key )
            if not hass_attr:
                raise IntegrationAttributeError( f'Missing HAss API attribute {hass_attr_type}' )
            if not hass_attr.value.strip():
                raise IntegrationAttributeError( f'Missing HAss API attribute value for {hass_attr_type}' )

            options_key = attr_to_api_option_key[hass_attr_type]
            api_options[options_key] = hass_attr.value
            continue
        
        logger.debug( f'Home Assistant client options: {api_options}' )
        return HassClient( api_options = api_options )

    @property
    def should_add_alarm_events( self ) -> bool:
        attribute = self._hass_attr_type_to_attribute.get( HassAttributeType.ADD_ALARM_EVENTS )
        if attribute:
            return str_to_bool( attribute.value )
        return False
        
    def fetch_hass_states_from_api( self, verbose : bool = True ) -> Dict[ str, HassState ]:
        if verbose:
            logger.debug( 'Getting current HASS states.' )
        
        if not self.hass_client:
            logger.warning('HASS client not available - cannot fetch states')
            return {}
            
        try:
            hass_entity_id_to_state = dict()
            for hass_state in self.hass_client.states():
                hass_entity_id = hass_state.entity_id
                hass_entity_id_to_state[hass_entity_id] = hass_state
                continue

            return hass_entity_id_to_state
        except Exception as e:
            error_msg = f'Failed to fetch HASS states: {e}'
            logger.warning(error_msg)
            self._update_health_status(IntegrationHealthStatusType.CONNECTION_ERROR, error_msg)
            return {}
    
    async def fetch_hass_states_from_api_async( self, verbose : bool = True ) -> Dict[ str, HassState ]:
        """
        Async version of fetch_hass_states_from_api for use in async contexts (monitors).
        Uses sync_to_async to properly handle the synchronous API call.
        """
        return await sync_to_async(
            self.fetch_hass_states_from_api,
            thread_sensitive=True
        )(verbose=verbose)
    
    def get_health_status(self) -> IntegrationHealthStatus:
        """Get the current health status of the HASS integration."""
        return self._health_status
    
    def _update_health_status(self, status: IntegrationHealthStatusType, error_message: str = None):
        """Update the health status of this integration."""
        old_status = self._health_status.status
        
        # Update health status
        self._health_status = IntegrationHealthStatus(
            status=status,
            last_check=datetimeproxy.now(),
            error_message=error_message,
            error_count=self._health_status.error_count + (1 if status.is_error else 0)
        )
        
        # Log status changes
        if old_status != status:
            if status == IntegrationHealthStatusType.HEALTHY:
                logger.info('HASS integration is now healthy')
            else:
                logger.warning(f'HASS integration health status changed to {status.value}: {error_message}')
    
    def test_connection(self) -> bool:
        """Test the connection to HASS API and update health status."""
        try:
            if not self.hass_client:
                self._update_health_status(IntegrationHealthStatusType.CONFIG_ERROR, "HASS client not configured")
                return False
            
            # Try to fetch states to test connection
            states = self.fetch_hass_states_from_api(verbose=False)
            if states is not None:
                self._update_health_status(IntegrationHealthStatusType.HEALTHY)
                return True
            else:
                self._update_health_status(IntegrationHealthStatusType.CONNECTION_ERROR, "Failed to fetch states from HASS API")
                return False
                
        except Exception as e:
            error_msg = f'Connection test failed: {e}'
            logger.debug(error_msg)
            self._update_health_status(IntegrationHealthStatusType.CONNECTION_ERROR, error_msg)
            return False
    
    def test_client_with_attributes(self, hass_attr_type_to_attribute: Dict[HassAttributeType, IntegrationAttribute]) -> Dict[str, any]:
        """
        Test API connectivity using provided attributes without affecting manager state.
        
        Args:
            hass_attr_type_to_attribute: Dictionary mapping attribute types to attribute objects
            
        Returns:
            Dictionary with validation result:
            {
                'success': bool,
                'error_message': str or None,
                'error_type': 'config'|'connection'|'auth'|'unknown' or None
            }
        """
        try:
            # Create temporary client with provided attributes
            temp_client = self.create_hass_client(hass_attr_type_to_attribute)
            
            # Test basic API connectivity
            states = temp_client.states()
            if states is not None:
                # Successful API call
                return {
                    'success': True,
                    'error_message': None,
                    'error_type': None
                }
            else:
                return {
                    'success': False,
                    'error_message': 'Failed to fetch states from Home Assistant API',
                    'error_type': 'connection'
                }
                
        except IntegrationError as e:
            return {
                'success': False,
                'error_message': str(e),
                'error_type': 'config'
            }
        except IntegrationAttributeError as e:
            return {
                'success': False,
                'error_message': str(e),
                'error_type': 'config'
            }
        except Exception as e:
            error_msg = str(e).lower()
            
            # Categorize common error types for better user feedback
            if any(keyword in error_msg for keyword in ['auth', 'unauthorized', 'forbidden', 'token', 'credential']):
                error_type = 'auth'
                user_message = f'Authentication failed: {e}'
            elif any(keyword in error_msg for keyword in ['connect', 'network', 'timeout', 'unreachable', 'resolve']):
                error_type = 'connection'  
                user_message = f'Cannot connect to Home Assistant: {e}'
            else:
                error_type = 'unknown'
                user_message = f'API test failed: {e}'
            
            return {
                'success': False,
                'error_message': user_message,
                'error_type': error_type
            }
    
    def validate_configuration(self, integration_attributes: List[IntegrationAttribute]) -> Dict[str, any]:
        """
        Validate HASS configuration using provided attributes.
        
        Args:
            integration_attributes: List of IntegrationAttribute objects
            
        Returns:
            Dictionary with validation result (same format as test_client_with_attributes)
        """
        try:
            # Build attribute mapping without enforcing requirements (for validation testing)
            hass_attr_type_to_attribute = self._build_hass_attr_type_to_attribute_map(
                integration_attributes=integration_attributes,
                enforce_requirements=False
            )
            
            # Use existing test method
            return self.test_client_with_attributes(hass_attr_type_to_attribute)
            
        except Exception as e:
            logger.exception(f'Error in HASS configuration validation: {e}')
            return {
                'success': False,
                'error_message': f'Configuration validation failed: {e}',
                'error_type': 'unknown'
            }
    
    def _build_hass_attr_type_to_attribute_map(
            self, 
            integration_attributes: List[IntegrationAttribute], 
            enforce_requirements: bool = True) -> Dict[HassAttributeType, IntegrationAttribute]:
        """Build mapping from HassAttributeType to IntegrationAttribute.
        
        Args:
            integration_attributes: List of IntegrationAttribute objects
            enforce_requirements: If True, raise errors for missing required attributes
            
        Returns:
            Dictionary mapping HassAttributeType to IntegrationAttribute
        """
        hass_attr_type_to_attribute = {}
        integration_key_to_attribute = {attr.integration_key: attr for attr in integration_attributes}
        
        for hass_attr_type in HassAttributeType:
            integration_key = IntegrationKey(
                integration_id = HassMetaData.integration_id,
                integration_name = str(hass_attr_type),
            )
            hass_attr = integration_key_to_attribute.get(integration_key)
            
            if not hass_attr:
                if enforce_requirements and hass_attr_type.is_required:
                    raise IntegrationAttributeError(f'Missing HASS attribute {hass_attr_type}')
                else:
                    continue
                    
            if enforce_requirements and hass_attr.is_required and not hass_attr.value.strip():
                raise IntegrationAttributeError(f'Missing HASS attribute value for {hass_attr_type}')
            
            hass_attr_type_to_attribute[hass_attr_type] = hass_attr
            
        return hass_attr_type_to_attribute
