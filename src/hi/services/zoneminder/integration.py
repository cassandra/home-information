import logging
from typing import List, Optional

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoSnapshot, VideoStream
from hi.apps.entity.enums import VideoStreamType, VideoStreamMode
from hi.apps.entity.constants import VideoStreamMetadataKeys
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.system.enums import HealthStatusType
from hi.apps.system.health_status_provider import HealthStatusProvider

from hi.integrations.connect.integration_controller import IntegrationController
from hi.integrations.connect.integration_gateway import IntegrationGateway
from hi.integrations.connect.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.connect.integration_synchronizer import IntegrationSynchronizer
from hi.integrations.models import IntegrationAttribute
from hi.integrations.transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .constants import ZmDetailKeys
from .zm_controller import ZoneMinderController
from .zm_manage_view_pane import ZmManageViewPane
from .zm_manager import ZoneMinderManager
from .zm_metadata import ZmMetaData
from .zm_sync import ZoneMinderSynchronizer
from .monitors import ZoneMinderMonitor
from .zm_mixins import ZoneMinderMixin

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway, ZoneMinderMixin ):

    def get_metadata(self) -> IntegrationMetaData:
        return ZmMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return ZmManageViewPane()
    
    def get_monitor(self) -> PeriodicMonitor:
        return ZoneMinderMonitor()
    
    def get_controller(self) -> IntegrationController:
        return ZoneMinderController()
    
    def notify_settings_changed(self):
        """Notify ZoneMinder integration that settings have changed.
        
        Delegates to ZoneMinderManager to reload configuration and notify monitors.
        """
        try:
            zm_manager = ZoneMinderManager()
            zm_manager.notify_settings_changed()
            logger.debug('ZoneMinder integration notified of settings change')
        except Exception as e:
            logger.exception(f'Error notifying ZoneMinder integration of settings change: {e}')
    
    def get_health_status_provider(self) -> HealthStatusProvider:
        return ZoneMinderManager()

    def get_synchronizer(self) -> IntegrationSynchronizer:
        return ZoneMinderSynchronizer()

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """Schema-only validation; delegates to ZoneMinderManager."""
        try:
            zm_manager = ZoneMinderManager()
            return zm_manager.validate_configuration(integration_attributes)
        except Exception as e:
            logger.exception(f'Error validating ZoneMinder integration configuration: {e}')
            return IntegrationValidationResult.error(
                status=HealthStatusType.WARNING,
                error_message=f'Configuration validation failed: {e}'
            )

    def validate_access(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """Live access validation probe; delegates to ZoneMinderManager."""
        try:
            zm_manager = ZoneMinderManager()
            return zm_manager.validate_access(
                integration_attributes=integration_attributes,
                timeout_secs=timeout_secs,
            )
        except Exception as e:
            logger.exception(f'Error in ZoneMinder access validation: {e}')
            return ConnectionTestResult.failure(f'Access validation error: {e}')
    
    def get_entity_video_snapshot(self, entity: Entity) -> Optional[VideoSnapshot]:
        """Return a fresh still frame for the ZoneMinder monitor backing
        this entity (``nph-zms?mode=single``). Returns None when the
        entity isn't a ZM monitor or the integration_name can't be
        parsed."""
        if not entity.has_video_snapshot:
            return None

        if not ( entity.integration_id == ZmMetaData.integration_id
                 and entity.integration_name
                 and entity.integration_name.startswith(
                     self.zm_manager().ZM_MONITOR_INTEGRATION_NAME_PREFIX )):
            return None

        try:
            monitor_id = int( entity.integration_name.split('.')[1] )
        except ( IndexError, ValueError ):
            logger.warning(
                f'Could not parse monitor ID from entity integration name: '
                f'{entity.integration_name}'
            )
            return None

        return VideoSnapshot(
            source_url = self.zm_manager().get_video_snapshot_url( monitor_id ),
            metadata = { 'monitor_id': monitor_id },
        )

    def get_entity_video_stream(self, entity: Entity) -> Optional[VideoStream]:
        """Get entity's primary video stream (typically live)"""
        if not entity.has_video_stream:
            return None
            
        # Check if this is a ZoneMinder camera entity
        if (entity.integration_id == ZmMetaData.integration_id
                and entity.integration_name
                and entity.integration_name.startswith(
                    self.zm_manager().ZM_MONITOR_INTEGRATION_NAME_PREFIX)):
            
            # Extract monitor ID from integration name (format: "monitor.{id}")
            try:
                monitor_id = int(entity.integration_name.split('.')[1])
                video_url = self.zm_manager().get_video_stream_url(monitor_id)
                
                return VideoStream(
                    stream_type=VideoStreamType.MJPEG,
                    source_url=video_url,
                    metadata={
                        'monitor_id': monitor_id,
                        VideoStreamMetadataKeys.STREAM_MODE: str(VideoStreamMode.LIVE)
                    }
                )
            except (IndexError, ValueError):
                logger.warning(f"Could not parse monitor ID from entity integration name:"
                               f" {entity.integration_name}")
                
        return None
        
    def get_sensor_response_event_snapshot_url(
            self,
            sensor_response: SensorResponse) -> Optional[str]:
        """Per-event snapshot URL for a ZM SensorResponse. Reads the
        event_id from detail_attrs (where the monitor stores it on
        every START / END row), builds the portal URL fresh each
        call so an operator-side portal-URL change auto-heals every
        historical row."""
        if not sensor_response.has_event_video_snapshot:
            return None
        event_id_fieldname = ZmDetailKeys.EVENT_ID_ATTR_NAME
        if not sensor_response.detail_attrs:
            return None
        raw_event_id = sensor_response.detail_attrs.get(event_id_fieldname)
        if raw_event_id is None:
            return None
        try:
            event_id = int(raw_event_id)
        except (ValueError, TypeError):
            logger.warning(
                'Could not parse event ID from ZM sensor response: %s',
                sensor_response.detail_attrs,
            )
            return None
        return self.zm_manager().get_event_snapshot_url(event_id=event_id)

    def get_sensor_response_video_stream(
            self,
            sensor_response: SensorResponse) -> Optional[VideoStream]:
        """Get video stream from sensor response (recorded events)"""
        # if not sensor_response.has_event_video_clip:
        #     return None

        event_id_fieldname = ZmDetailKeys.EVENT_ID_ATTR_NAME
        
        # Check if this sensor response has an event ID in its detail_attrs
        if (sensor_response.detail_attrs
                and event_id_fieldname in sensor_response.detail_attrs):
            
            try:
                event_id = int(sensor_response.detail_attrs[event_id_fieldname])
                video_url = self.zm_manager().get_event_video_stream_url(event_id)

                # Extract duration from detail_attrs if available
                metadata = {
                    event_id_fieldname: event_id,
                    VideoStreamMetadataKeys.STREAM_MODE: str(VideoStreamMode.RECORDED)
                }

                # Look for duration in detail_attrs using the ZoneMinder constant
                if ZmDetailKeys.DURATION_SECS in sensor_response.detail_attrs:
                    try:
                        duration_secs = float(sensor_response.detail_attrs[ZmDetailKeys.DURATION_SECS])
                        metadata[VideoStreamMetadataKeys.DURATION_SECS] = int(duration_secs)
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse duration from sensor response:"
                                     f" {sensor_response.detail_attrs.get(ZmDetailKeys.DURATION_SECS)}")

                return VideoStream(
                    stream_type=VideoStreamType.MJPEG,
                    source_url=video_url,
                    metadata=metadata
                )
            except (ValueError, TypeError):
                logger.warning(f"Could not parse event ID from sensor response:"
                               f" {sensor_response.detail_attrs}")
                
        return None
