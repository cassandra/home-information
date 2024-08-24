import logging
import pyzm.api as pyzm_api
from pyzm.helpers.Monitor import Monitor as ZmMonitor
from typing import Dict

from django.db import transaction

from hi.apps.common.database_lock import ExclusionLockContext
from hi.apps.common.processing_result import ProcessingResult
from hi.apps.common.singleton import Singleton
from hi.apps.entity.enums import (
    AttributeName,
    EntityType,
    AttributeValueType,
    AttributeType,
)
from hi.apps.entity.models import Entity, Attribute

from hi.apps.entity_helpers import EntityHelpers

from hi.integrations.core.enums import IntegrationType
from hi.integrations.core.exceptions import IntegrationPropertyError
from hi.integrations.core.models import Integration

from .enums import (
    ZmPropertyName,
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
        property_dict = zm_integration.property_dict
        for zm_prop_name in ZmPropertyName:
            zm_prop = property_dict.get( zm_prop_name.name )
            if not zm_prop:
                raise IntegrationPropertyError( f'Missing ZM property {zm_prop_name.name}' ) 
            if zm_prop.is_required and not zm_prop.value.strip():
                raise IntegrationPropertyError( f'Missing ZM property value for {zm_prop_name.name}' ) 

            continue
        
        api_options = {
            'apiurl': property_dict.get( ZmPropertyName.API_URL.name ).value,
            'portalurl': property_dict.get( ZmPropertyName.PORTAL_URL.name ).value,
            'user': property_dict.get( ZmPropertyName.API_USER.name ).value,
            'password': property_dict.get( ZmPropertyName.API_PASSWORD.name ).value,
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

        attribute_queryset = Attribute.objects.select_related( 'entity' ). filter(
            name = AttributeName.INTEGRATION_SOURCE,
            value = IntegrationType.ZONEMINDER.name,
        )
        for attribute in attribute_queryset:
            zm_entity = attribute.entity
            attribute_map = zm_entity.get_attribute_map()
            try:
                attribute = attribute_map.get( str(ZmAttributeName.ZM_MONITOR_ID) )
                zm_id = int( attribute.value )
            except ( TypeError, ValueError ):
                result.error_list.append( f'ZM entity found without valid ZM Id: {zm_entity}' )
                zm_id = 1000000 + zm_entity.id  # We need a (unique) placeholder (will remove this later)
            zm_id_to_entity[zm_id] = zm_entity
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
        
        with transaction.atomic():

            entity = Entity.objects.create(
                name = monitor.name(),
                entity_type_str = str(EntityType.CAMERA),
            )
            Attribute.objects.create(
                entity = entity,
                name = AttributeName.INTEGRATION_SOURCE,
                value = IntegrationType.ZONEMINDER.name,
                attribute_value_type_str = str( AttributeValueType.STRING ),
                attribute_type_str = str( AttributeType.PREDEFINED ),
                is_editable = False,
                is_required = True,
            )
            Attribute.objects.create(
                entity = entity,
                name = ZmAttributeName.ZM_MONITOR_ID,
                value = str( monitor.id() ),
                attribute_value_type_str = str( AttributeValueType.INTEGER ),
                attribute_type_str = str( AttributeType.PREDEFINED ),
                is_editable = False,
                is_required = True,
            )

            EntityHelpers.create_video_stream_sensor(
                entity = entity,
            )
            EntityHelpers.create_movement_sensor(
                entity = entity,
            )
            EntityHelpers.create_discrete_controller(
                entity = entity,
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
    
