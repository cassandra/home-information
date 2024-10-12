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

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.exceptions import IntegrationAttributeError
from hi.integrations.core.models import Integration, IntegrationId

from .enums import (
    ZmAttributeName,
    ZmMonitorState,
)

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
            logger.warning( 'ZoneMinder is already loading.' )
            return
        try:
            self._is_loading = True
            self._zm_client = self.create_zm_client()
        
        finally:
            self._is_loading = False
            logger.debug( 'ZoneMinder loading completed.' )
        return

    def create_zm_client(self):
        try:
            zm_integration = Integration.objects.get( integration_type_str = str(IntegrationType.ZONEMINDER) )
        except Integration.DoesNotExist:
            logger.debug( 'ZoneMinder integration is not implemented.' )

        if not zm_integration.is_enabled:
            logger.debug( 'ZoneMinder integration is not enabled.' )
            return None

        # Verify integration
        attribute_dict = zm_integration.attribute_dict
        for zm_attr_name in ZmAttributeName:
            zm_prop = attribute_dict.get( zm_attr_name.name )
            if not zm_prop:
                raise IntegrationAttributeError( f'Missing ZM attribute {zm_attr_name.name}' ) 
            if zm_prop.is_required and not zm_prop.value.strip():
                raise IntegrationAttributeError( f'Missing ZM attribute value for {zm_attr_name.name}' ) 

            continue
        
        api_options = {
            'apiurl': attribute_dict.get( ZmAttributeName.API_URL.name ).value,
            'portalurl': attribute_dict.get( ZmAttributeName.PORTAL_URL.name ).value,
            'user': attribute_dict.get( ZmAttributeName.API_USER.name ).value,
            'password': attribute_dict.get( ZmAttributeName.API_PASSWORD.name ).value,
            # 'disable_ssl_cert_check': True
        }

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
                    
        zm_id_to_entity = self._get_zm_entities( result = result )
        result.message_list.append( f'Found {len(zm_id_to_entity)} existing ZM entities.' )

        zm_id_to_monitor = self._get_zm_monitors( result = result )
        result.message_list.append( f'Found {len(zm_id_to_monitor)} current ZM monitors.' )
        
        for zm_id, monitor in zm_id_to_monitor.items():
            entity = zm_id_to_entity.get( zm_id )
            if entity:
                self._update_entity( entity = entity,
                                     monitor = monitor,
                                     result = result )
            else:
                self._create_entity( monitor = monitor,
                                     result = result )
            continue
        
        for zm_id, entity in zm_id_to_entity.items():
            if zm_id not in zm_id_to_monitor:
                self._remove_entity( entity = entity,
                                     result = result )
            continue
        
        return result

    def _get_zm_entities( self, result : ProcessingResult ) -> Dict[ int, Entity ]:
        logger.debug( 'Getting existing ZM entities.' )
        zm_id_to_entity = dict()
        
        entity_queryset = Entity.objects.filter( integration_type_str = str(IntegrationType.ZONEMINDER) )
        for entity in entity_queryset:
            integration_id = entity.integration_id
            try:
                zm_id = int( integration_id.key )
            except ( TypeError, ValueError ):
                result.error_list.append( f'ZM entity found without valid ZM Id: {entity}' )
                zm_id = 1000000 + entity.id  # We need a (unique) placeholder (will remove this later)
            zm_id_to_entity[zm_id] = entity
            
            continue
        
        return zm_id_to_entity

    def _get_zm_monitors( self, result : ProcessingResult ) -> Dict[ int, ZmMonitor ]:
        
        logger.debug( 'Getting current ZM monitors.' )
        zm_id_to_monitor = dict()
        for zm_monitor in self.zm_client.monitors().list():
            zm_id = zm_monitor.id()
            
            result.message_list.append(
                '[ZM Monitor] Id:{} Name:{} Enabled:{} Status:{} Type:{} Dims:{}'.format(
                    zm_id,
                    zm_monitor.name(),
                    zm_monitor.enabled(),
                    zm_monitor.status(),
                    zm_monitor.type(),
                    zm_monitor.dimensions(),
                )
            )
            zm_id_to_monitor[zm_id] = zm_monitor
            continue

        return zm_id_to_monitor
    
    def _create_entity( self,
                        monitor  : ZmMonitor,
                        result   : ProcessingResult ):

        integration_id = IntegrationId(
            integration_type = IntegrationType.ZONEMINDER,
            key = str( monitor.id() ),
            
        )
        with transaction.atomic():

            entity = Entity(
                name = monitor.name(),
                entity_type_str = str(EntityType.CAMERA),
            )
            entity.integration_id = integration_id
            entity.save()
            HiModelHelper.create_video_stream_sensor(
                entity = entity,
                integration_id = integration_id,
            )
            HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_id = integration_id,
            )
            HiModelHelper.create_discrete_controller(
                entity = entity,
                integration_id = integration_id,
                name = f'{entity.name} State',
                value_list = [ str(x) for x in ZmMonitorState ],
            )
        result.message_list.append( f'Create new camera entity: {entity}' )
        return
    
    def _update_entity( self,
                        entity   : Entity,
                        monitor  : ZmMonitor,
                        result   : ProcessingResult ):

        # Currently nothing stored locally that will change (other than entity existence)

        result.message_list.append( f'No updates needed for camera entity: {entity}' )
        
        return
    
    def _remove_entity( self,
                        entity   : Entity,
                        result   : ProcessingResult ):
        entity.delete()  # Deletion cascades to attributes, positions, sensors, controllers, etc.
        result.message_list.append( f'Removed stale ZM entity: {entity}' )
        return
    
