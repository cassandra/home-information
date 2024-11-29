import logging
from pyzm.api import ZMApi
from pyzm.helpers.Monitor import Monitor as ZmMonitor
from pyzm.helpers.globals import logger as pyzm_logger
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
from hi.integrations.core.models import Integration, IntegrationAttribute

from .enums import (
    ZmAttributeType,
    ZmMonitorFunction,
)
from .zm_metadata import ZmMetaData

logger = logging.getLogger(__name__)
pyzm_logger.set_level( 0 )  # pyzm does not use standard 'logging' module. ugh.


class ZoneMinderManager( Singleton ):
    """
    References:
      ZM Api code: https://github.com/ZoneMinder/zoneminder/tree/master/web/api/app/Controller
      PyZM code: https://github.com/pliablepixels/pyzm/tree/357fdbd1937dab8027882598b61258ef43dc366a
    """

    VIDEO_STREAM_SENSOR_PREFIX = 'monitor.video_stream'
    MOVEMENT_SENSOR_PREFIX = 'monitor.motion'
    MONITOR_FUNCTION_SENSOR_PREFIX = 'monitor.function'
    
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
        """ Should be called when integration settings are changed. """
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
        for zm_attr_type in attr_to_api_option_key.keys():
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
        return ZMApi( options = api_options )
    
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
            integration_key = self._monitor_to_integration_key( zm_monitor_id = zm_monitor.id() )
            integration_key_to_monitor[integration_key] = zm_monitor
            
            logger.debug(
                '[ZM Monitor] Id:{} Name:{} Enabled:{} Status:{} Type:{} Dims:{}'.format(
                    zm_monitor.id(),
                    zm_monitor.name(),
                    zm_monitor.enabled(),
                    zm_monitor.status(),
                    zm_monitor.type(),
                    zm_monitor.dimensions(),
                )
            )
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

        with transaction.atomic():

            entity_integration_key = self._monitor_to_integration_key( zm_monitor_id = zm_monitor.id() )
            entity = Entity(
                name = zm_monitor.name(),
                entity_type_str = str(EntityType.CAMERA),
                can_user_delete = ZmMetaData.allow_entity_deletion,
            )
            entity.integration_key = entity_integration_key
            entity.save()
            
            HiModelHelper.create_video_stream_sensor(
                entity = entity,
                integration_key = self._sensor_to_integration_key(
                    sensor_prefix = self.VIDEO_STREAM_SENSOR_PREFIX,
                    zm_monitor_id = zm_monitor.id(),
                ),
            )
            HiModelHelper.create_movement_sensor(
                entity = entity,
                integration_key = self._sensor_to_integration_key(
                    sensor_prefix = self.MOVEMENT_SENSOR_PREFIX,
                    zm_monitor_id = zm_monitor.id(),
                ),
            )
            HiModelHelper.create_discrete_controller(
                entity = entity,
                integration_key = self._sensor_to_integration_key(
                    sensor_prefix = self.MONITOR_FUNCTION_SENSOR_PREFIX,
                    zm_monitor_id = zm_monitor.id(),
                ),
                name = f'{entity.name} Function',
                value_list = [ str(x) for x in ZmMonitorFunction ],
            )
        result.message_list.append( f'Create new camera entity: {entity}' )
        return
    
    def _update_entity( self,
                        entity      : Entity,
                        zm_monitor  : ZmMonitor,
                        result      : ProcessingResult ):

        if entity.name != zm_monitor.name():
            result.message_list.append(f'Name changed for {entity}. Setting to "{zm_monitor.name()}"')
            entity.name = zm_monitor.name()
            entity.save()
        else:
            result.message_list.append( f'No changes found for {entity}.' )
        return
    
    def _remove_entity( self,
                        entity  : Entity,
                        result  : ProcessingResult ):
        entity.delete()  # Deletion cascades to attributes, positions, sensors, controllers, etc.
        result.message_list.append( f'Removed stale ZM entity: {entity}' )
        return
    
    def _monitor_to_integration_key( self, zm_monitor_id  : ZmMonitor ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = str( zm_monitor_id ),
            
        )
    
    def _sensor_to_integration_key( self, sensor_prefix : str, zm_monitor_id  : int ) -> IntegrationKey:
        return IntegrationKey(
            integration_id = ZmMetaData.integration_id,
            integration_name = f'{sensor_prefix}.{zm_monitor_id}',
        )
    
    def get_zm_tzname(self) -> str:
        try:
            zm_integration = Integration.objects.get( integration_id = ZmMetaData.integration_id )
            integration_key = IntegrationKey(
                integration_id = ZmMetaData.integration_id,
                integration_name = str(ZmAttributeType.TIMEZONE),
            )
            integration_attribute = IntegrationAttribute.objects.filter(
                integration = zm_integration,
                integration_key_str = str(integration_key),
            ).first()
            if integration_attribute:
                return integration_attribute.value
            logger.error( 'ZoneMinder integration is not implemented.' )
                
        except IntegrationAttribute.DoesNotExist:
            logger.error( 'ZoneMinder timezone not found.' )

        return 'UTC'

    def get_video_stream_url( self, monitor_id : int ):
        return f'{self.zm_client.portal_url}/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=100&maxfps=30&monitor={monitor_id}'

    def get_event_video_stream_url( self, event_id : int ):
        return f'{self.zm_client.portal_url}/cgi-bin/nph-zms?mode=jpeg&scale=100&rate=100&maxfps=30&replay=single&source=event&event={event_id}'

