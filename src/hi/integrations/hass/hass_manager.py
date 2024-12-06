import logging
from threading import local
from typing import Dict

from django.db.models.signals import post_save, post_delete
from django.db import transaction
from django.dispatch import receiver

from hi.apps.common.singleton import Singleton
from hi.apps.common.utils import str_to_bool

from hi.integrations.core.exceptions import IntegrationAttributeError, IntegrationError
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.models import Integration, IntegrationAttribute

from .enums import HassAttributeType
from .hass_client import HassClient
from .hass_metadata import HassMetaData
from .hass_models import HassState

logger = logging.getLogger(__name__)


class HassManager( Singleton ):

    def __init_singleton__( self ):
        self._is_loading = False
        self._hass_attr_type_to_attribute = dict()
        self._hass_client = None
        self.reload()
        return

    @property
    def hass_client(self):
        return self._hass_client
    
    def reload( self ):
        """ Called when integration models are changed (via signals below). """
        if self._is_loading:
            logger.warning( 'HAss is already loading.' )
            return
        try:
            self._is_loading = True
            self._hass_attr_type_to_attribute = self._load_attributes()
            self._hass_client = self.create_hass_client( self._hass_attr_type_to_attribute )
            self.clear_caches()

        finally:
            self._is_loading = False
            logger.debug( 'HAss loading completed.' )
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
        
        hass_attr_type_to_attribute = dict()
        integration_key_to_attribute = hass_integration.attributes_by_integration_key
        for hass_attr_type in HassAttributeType:
            integration_key = IntegrationKey(
                integration_id = hass_integration.integration_id,
                integration_name = str(hass_attr_type),
            )
            hass_attr = integration_key_to_attribute.get( integration_key )
            if not hass_attr:
                if hass_attr_type.is_required:
                    raise IntegrationAttributeError( f'Missing HAss attribute {hass_attr_type}' )
                else:
                    continue
            if hass_attr.is_required and not hass_attr.value.strip():
                raise IntegrationAttributeError( f'Missing HAss attribute value for {hass_attr_type}' )
            
            hass_attr_type_to_attribute[hass_attr_type] = hass_attr
            continue

        return hass_attr_type_to_attribute
    
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
            logger.debug( 'Getting current HAss states.' )
            
        hass_entity_id_to_state = dict()
        for hass_state in self.hass_client.states():
            hass_entity_id = hass_state.entity_id
            hass_entity_id_to_state[hass_entity_id] = hass_state
            continue

        return hass_entity_id_to_state

    
_thread_local = local()


def do_hass_manager_reload():
    logger.debug( 'Reloading HassManager from model changes.')
    HassManager().reload()
    _thread_local.reload_registered = False
    return


@receiver( post_save, sender = Integration )
@receiver( post_save, sender = IntegrationAttribute )
@receiver( post_delete, sender = Integration )
@receiver( post_delete, sender = IntegrationAttribute )
def hass_manager_model_changed( sender, instance, **kwargs ):
    """
    Queue the EventManager.reload() call to execute after the transaction
    is committed.  This prevents reloading multiple times if multiple
    models saved as part of a transaction (which is the normal case for
    EventDefinition and its related models.)
    """

    if ( isinstance( instance, Integration )
         and ( instance.integration_id != HassMetaData.integration_id )):
        return
    if ( isinstance( instance, IntegrationAttribute )
         and ( instance.integration.integration_id != HassMetaData.integration_id )):
        return
    
    if not hasattr(_thread_local, "reload_registered"):
        _thread_local.reload_registered = False

    logger.debug( 'HassManager model change detected.')
        
    if not _thread_local.reload_registered:
        logger.debug( 'Queuing HassManager reload on model change.')
        _thread_local.reload_registered = True
        transaction.on_commit( do_hass_manager_reload )
    
    return
