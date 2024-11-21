import logging
import pyzm.api as pyzm_api
from pyzm.helpers.Monitor import Monitor as ZmMonitor
from typing import Dict

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.common.singleton import Singleton
from hi.apps.entity.enums import EntityType
from hi.apps.entity.models import Entity

from hi.apps.model_helper import HiModelHelper

from hi.integrations.core.exceptions import IntegrationAttributeError
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.models import Integration

from .enums import (
    ZmAttributeType,
    ZmMonitorState,
)
from .zm_metadata import ZmMetaData

logger = logging.getLogger(__name__)


class ZoneMinderManager( Singleton ):

    SYNCHRONIZATION_LOCK_NAME = 'zm_integration_sync'

    def __init_singleton__( self ):
        self._is_loading = False
        self._zm_client = None
        self.reload()
        return

    @property
    def zm_client(self):
        # Docs: https://pyzm.readthedocs.io/en/latest/
        return self._zm_client
    
    def reload( self ):
        if self._is_loading:
            logger.warning( 'ZoneMinder manager is already loading.' )
            return
        try:
            self._is_loading = True
            self._zm_client = self.create_zm_client()
        
        finally:
            self._is_loading = False
            logger.debug( 'ZoneMinder manager loading completed.' )
        return

    def create_zm_client(self):
        try:
            zm_integration = Integration.objects.get( integration_id = ZmMetaData.integration_id )
        except Integration.DoesNotExist:
            logger.debug( 'ZoneMinder integration is not implemented.' )

        if not zm_integration.is_enabled:
            logger.debug( 'ZoneMinder integration is not enabled.' )
            return None

        # Verify integration and build API data payload
        api_options = {
            # 'disable_ssl_cert_check': True
        }
        attr_to_api_option_key = {
            ZmAttributeType.API_URL: 'apiurl',
            ZmAttributeType.PORTAL_URL: 'portalurl',
            ZmAttributeType.API_USER: 'user',
            ZmAttributeType.API_PASSWORD: 'password',
        }
        
        attribute_dict = zm_integration.attributes_by_integration_key
        for zm_attr_type in ZmAttributeType:
            integration_key = IntegrationKey(
                integration_id = zm_integration.integration_id,
                integration_name = str(zm_attr_type),
            )
            zm_attr = attribute_dict.get( integration_key )
            if not zm_attr:
                raise IntegrationAttributeError( f'Missing ZM attribute {zm_attr_type}' ) 
            if zm_attr.is_required and not zm_attr.value.strip():
                raise IntegrationAttributeError( f'Missing ZM attribute value for {zm_attr_type}' )

            if zm_attr_type in attr_to_api_option_key:
                options_key = attr_to_api_option_key[zm_attr_type]
                api_options[options_key] = zm_attr.value
            
            continue
        
        logger.debug( f'ZoneMinder client options: {api_options}' )
        
        return pyzm_api.ZMApi( options = api_options )
        
    def sync( self ) -> ProcessingResult:
        try:
            with ExclusionLockContext( name = self.SYNCHRONIZATION_LOCK_NAME ):
                logger.debug( 'ZoneMinder integration sync started.' )
                return self._sync_helper()
        except RuntimeError as e:
            return ProcessingResult(
                title = 'ZM Sync Result',
                error_list = [ str(e) ],
            )
        finally:
            logger.debug( 'ZoneMinder integration sync ended.' )
    
    def _sync_helper( self ) -> ProcessingResult:
        result = ProcessingResult( title = 'ZM Sync Result' )

        zm_client = self.zm_client
        if not zm_client:
            logger.debug( 'ZoneMinder client not created. ZM integration disabled?' )
            result.error_list.append( 'Sync problem. ZM integration disabled?' )
            return result
                    
        integration_key_to_monitor = self._fetch_zm_monitors( result = result )
        result.message_list.append( f'Found {len(integration_key_to_monitor)} current ZM monitors.' )
        
        integration_key_to_entity = self._get_existing_zm_entities( result = result )
        result.message_list.append( f'Found {len(integration_key_to_entity)} existing ZM entities.' )

        with transaction.atomic():
            for integration_key, zm_monitor in integration_key_to_monitor.items():
                entity = integration_key_to_entity.get( integration_key )
                if entity:
                    self._update_entity( entity = entity,
                                         zm_monitor = zm_monitor,
                                         result = result )
                else:
                    self._create_entity( zm_monitor = zm_monitor,
                                         result = result )
                continue

            for integration_key, entity in integration_key_to_entity.items():
                if integration_key not in integration_key_to_monitor:
                    self._remove_entity( entity = entity,
                                         result = result )
                continue
        
        return result

    def _fetch_zm_monitors( self, result : ProcessingResult ) -> Dict[ IntegrationKey, ZmMonitor ]:
        
        logger.debug( 'Getting current ZM monitors.' )
        integration_key_to_monitor = dict()
        for zm_monitor in self.zm_client.monitors().list():
            integration_key = self._monitor_to_integration_key( zm_monitor = zm_monitor )
            
            result.message_list.append(
                '[ZM Monitor] Id:{} Name:{} Enabled:{} Status:{} Type:{} Dims:{}'.format(
                    zm_monitor.id(),
                    zm_monitor.name(),
                    zm_monitor.enabled(),
                    zm_monitor.status(),
                    zm_monitor.type(),
                    zm_monitor.dimensions(),
                )
            )
            integration_key_to_monitor[integration_key] = zm_monitor
            continue

        return integration_key_to_monitor
    
    def _get_existing_zm_entities( self, result : ProcessingResult ) -> Dict[ IntegrationKey, Entity ]:
        logger.debug( 'Getting existing ZM entities.' )
        integration_key_to_entity = dict()
        
        entity_queryset = Entity.objects.filter( integration_id = ZmMetaData.integration_id )
        for entity in entity_queryset:
            integration_key = entity.integration_key
            if not integration_key:
                result.error_list.append( f'ZM entity found without integration name: {entity}' )
                mock_monitor_id = 1000000 + entity.id  # We need a (unique) placeholder (will remove later)
                integration_key = IntegrationKey(
                    integration_id = ZmMetaData.integration_id,
                    integration_name = str( mock_monitor_id ),
                )
            integration_key_to_entity[integration_key] = entity
            continue
        
        return integration_key_to_entity

    def _create_entity( self,
                        zm_monitor  : ZmMonitor,
                        result      : ProcessingResult ):

        integration_key = self._monitor_to_integration_key( zm_monitor = zm_monitor )
        with transaction.atomic():

            entity = Entity(
                name = zm_monitor.name(),
                entity_type_str = str(EntityType.CAMERA),
                can_user_delete = ZmMetaData.allow_entity_deletion,
            )
            entity.integration_key = integration_key
            entity.save()
            HiModelHelper.create_video_stream_sensor(
                entity = entity,
                integration_key = integration_key,
            )
            HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_key = integration_key,
            )
            HiModelHelper.create_discrete_controller(
                entity = entity,
                integration_key = integration_key,
                name = f'{entity.name} State',
                value_list = [ str(x) for x in ZmMonitorState ],
            )
        result.message_list.append( f'Create new camera entity: {entity}' )
        return
    
    def _update_entity( self,
                        entity     : Entity,
                        zm_monitor  : ZmMonitor,
                        result     : ProcessingResult ):

        # Currently nothing stored locally that will change (other than entity existence)

        result.message_list.append( f'No updates needed for camera entity: {entity}' )
        
        return
    
    def _remove_entity( self,
                        entity   : Entity,
                        result   : ProcessingResult ):
        entity.delete()  # Deletion cascades to attributes, positions, sensors, controllers, etc.
        result.message_list.append( f'Removed stale ZM entity: {entity}' )
        return
    
    def _monitor_to_integration_key( self, zm_monitor  : ZmMonitor ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = str( zm_monitor.id() ),
            
        )
    
