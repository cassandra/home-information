import logging
from asgiref.sync import sync_to_async
from typing import Dict, List

from hi.apps.common.singleton_manager import SingletonManager
from hi.apps.common.utils import str_to_bool
from hi.apps.system.api_owner_mixin import ApiOwnerMixin
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_mixin import HealthStatusMixin

from hi.integrations.exceptions import (
    IntegrationAttributeError,
    IntegrationError,
    IntegrationDisabledError,
)
from hi.integrations.transient_models import (
    IntegrationKey,
    IntegrationValidationResult,
)
from hi.integrations.models import Integration, IntegrationAttribute

from .enums import HassAttributeType
from .hass_client import HassClient
from .hass_client_factory import HassClientFactory
from .hass_metadata import HassMetaData
from .hass_models import HassState

logger = logging.getLogger(__name__)


class HassManager( SingletonManager, HealthStatusMixin, ApiOwnerMixin ):

    def __init_singleton__( self ):
        super().__init_singleton__()
        self._hass_attr_type_to_attribute = dict()
        self._hass_client = None
        self._client_factory = HassClientFactory()

        self._change_listeners = set()

        return
    
    def register_change_listener( self, callback ):
        if callback not in self._change_listeners:
            logger.debug( f'Adding HASS setting change listener from {callback.__module__}' )
            self._change_listeners.add( callback )
        else:
            logger.debug( f'HASS setting change listener from'
                          f' {callback.__module__} already registered, skipping duplicate' )
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

    def _reload_implementation( self ):
        """
        Perform the actual HASS manager reload work.
        Called by SingletonManager with appropriate locks already held.
        """
        try:
            self._hass_attr_type_to_attribute = self._load_attributes()
            self._hass_client = self.create_hass_client( self._hass_attr_type_to_attribute )
            self.clear_caches()
            self.update_health_status(HealthStatusType.HEALTHY)

        except IntegrationDisabledError:
            msg = 'HASS integration disabled'
            logger.info(msg)
            self.update_health_status( HealthStatusType.DISABLED, msg  )

        except IntegrationError as e:
            error_msg = f'HASS integration configuration error: {e}'
            logger.error(error_msg)
            self.update_health_status( HealthStatusType.CONFIG_ERROR, error_msg )

        except IntegrationAttributeError as e:
            error_msg = f'HASS integration attribute error: {e}'
            logger.error(error_msg)
            self.update_health_status( HealthStatusType.CONFIG_ERROR, error_msg )

        except Exception as e:
            error_msg = f'Unexpected error loading HASS configuration: {e}'
            logger.exception(error_msg)
            self.update_health_status( HealthStatusType.TEMPORARY_ERROR, error_msg )
        return

    def clear_caches(self):
        return

    def _load_attributes(self) -> Dict[ HassAttributeType, IntegrationAttribute ]:
        try:
            hass_integration = Integration.objects.get( integration_id = HassMetaData.integration_id )
        except Integration.DoesNotExist:
            raise IntegrationError( 'Home Assistant integration is not implemented.' )
        
        if not hass_integration.is_enabled:
            raise IntegrationDisabledError( 'Home Assistant integration is not enabled.' )
        
        integration_attributes = list(hass_integration.attributes.all())
        return self._build_hass_attr_type_to_attribute_map(
            integration_attributes=integration_attributes,
            enforce_requirements=True
        )
    
    def create_hass_client(
            self,
            hass_attr_type_to_attribute : Dict[ HassAttributeType, IntegrationAttribute ] ) -> HassClient:
        """Create a HassClient from integration attributes.

        Delegates to HassClientFactory for actual client creation.
        """
        return self._client_factory.create_client(hass_attr_type_to_attribute)

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
            
        with self.api_call_context( 'hass_states' ):
            hass_state_sequence = self.hass_client.states()

        hass_entity_id_to_state = dict()
        for hass_state in hass_state_sequence:
            hass_entity_id = hass_state.entity_id
            hass_entity_id_to_state[hass_entity_id] = hass_state
            continue

        return hass_entity_id_to_state
    
    async def fetch_hass_states_from_api_async( self, verbose : bool = True ) -> Dict[ str, HassState ]:
        """
        Async version of fetch_hass_states_from_api for use in async contexts (monitors).
        Uses sync_to_async to properly handle the synchronous API call.
        """
        return await sync_to_async(
            self.fetch_hass_states_from_api,
            thread_sensitive=True
        )(verbose=verbose)
    
    def test_connection(self) -> bool:
        """Test the connection to HASS API and update health status."""
        try:
            if not self.hass_client:
                self.update_health_status(HealthStatusType.CONFIG_ERROR,
                                          "HASS client not configured")
                return False
            
            # Try to fetch states to test connection
            states = self.fetch_hass_states_from_api(verbose=False)
            if states is not None:
                self.update_health_status(HealthStatusType.HEALTHY)
                return True
            else:
                self.update_health_status(HealthStatusType.CONNECTION_ERROR,
                                          "Failed to fetch states from HASS API")
                return False
                
        except Exception as e:
            error_msg = f'Connection test failed: {e}'
            logger.debug(error_msg)
            self.update_health_status(HealthStatusType.CONNECTION_ERROR, error_msg)
            return False
    
    def test_client_with_attributes(
            self,
            hass_attr_type_to_attribute: Dict[HassAttributeType, IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """
        Test API connectivity using provided attributes without affecting manager state.

        Args:
            hass_attr_type_to_attribute: Dictionary mapping attribute types to attribute objects

        Returns:
            IntegrationValidationResult with test results
        """
        try:
            # Create temporary client with provided attributes
            temp_client = self._client_factory.create_client(hass_attr_type_to_attribute)
            # Test the client
            return self._client_factory.test_client(temp_client)

        except IntegrationError as e:
            return IntegrationValidationResult.error(
                status=HealthStatusType.CONFIG_ERROR,
                error_message=str(e)
            )
        except IntegrationAttributeError as e:
            return IntegrationValidationResult.error(
                status=HealthStatusType.CONFIG_ERROR,
                error_message=str(e)
            )
    
    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]) -> IntegrationValidationResult:
        """
        Validate HASS configuration using provided attributes.

        Args:
            integration_attributes: List of IntegrationAttribute objects

        Returns:
            IntegrationValidationResult with validation results
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
            return IntegrationValidationResult.error(
                status=HealthStatusType.TEMPORARY_ERROR,
                error_message=f'Configuration validation failed: {e}'
            )
    
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
