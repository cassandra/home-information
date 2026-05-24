import logging
from typing import List, Optional

from hi.apps.entity.enums import VideoStreamType
from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoSnapshot, VideoStream
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
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

from .frigate_controller import FrigateController
from .frigate_manage_view_pane import FrigateManageViewPane
from .frigate_manager import FrigateManager
from .frigate_metadata import FrigateMetaData
from .frigate_mixins import FrigateMixin
from .frigate_sync import FrigateSynchronizer
from .monitors import FrigateMonitor

logger = logging.getLogger(__name__)


class FrigateGateway( IntegrationGateway, FrigateMixin ):
    """Framework entry point for the Frigate integration.

    Auto-discovered by ``IntegrationManager.discover_defined_integrations``
    because this module exposes an ``IntegrationGateway`` subclass and
    lives under ``hi.services.*``. Delegates almost everything to the
    other pieces of the integration; see
    ``docs/dev/integrations/integration-guidelines.md`` for the
    contract this class satisfies.
    """

    def get_metadata(self) -> IntegrationMetaData:
        return FrigateMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return FrigateManageViewPane()

    def get_monitor(self) -> PeriodicMonitor:
        return FrigateMonitor()

    def get_controller(self) -> IntegrationController:
        return FrigateController()

    def notify_settings_changed(self):
        try:
            FrigateManager().notify_settings_changed()
            logger.debug( 'Frigate integration notified of settings change.' )
        except Exception as e:
            logger.exception(
                f'Error notifying Frigate integration of settings change: {e}'
            )

    def get_health_status_provider(self) -> HealthStatusProvider:
        return FrigateManager()

    def get_synchronizer(self) -> IntegrationSynchronizer:
        return FrigateSynchronizer()

    def validate_configuration(
            self,
            integration_attributes : List[ IntegrationAttribute ],
    ) -> IntegrationValidationResult:
        try:
            return FrigateManager().validate_configuration(
                integration_attributes = integration_attributes,
            )
        except Exception as e:
            logger.exception( f'Error validating Frigate configuration: {e}' )
            return IntegrationValidationResult.error(
                status = HealthStatusType.WARNING,
                error_message = f'Configuration validation failed: {e}',
            )

    def validate_access(
            self,
            integration_attributes : List[ IntegrationAttribute ],
            timeout_secs           : Optional[ float ],
    ) -> ConnectionTestResult:
        try:
            return FrigateManager().validate_access(
                integration_attributes = integration_attributes,
                timeout_secs = timeout_secs,
            )
        except Exception as e:
            logger.exception( f'Error in Frigate access validation: {e}' )
            return ConnectionTestResult.failure( f'Access validation error: {e}' )

    def get_entity_video_snapshot(self, entity : Entity) -> Optional[ VideoSnapshot ]:
        """Live still-frame for the Frigate camera backing this entity
        (``/api/<camera>/latest.jpg``). Returns ``None`` when the
        entity isn't a Frigate camera, when ``has_video_snapshot`` is
        off (operator opt-out), or when the integration client isn't
        ready."""
        if not entity.has_video_snapshot:
            return None
        if entity.integration_id != FrigateMetaData.integration_id:
            return None

        prefix = FrigateManager.FRIGATE_CAMERA_INTEGRATION_NAME_PREFIX + '.'
        integration_name = entity.integration_name or ''
        if not integration_name.startswith( prefix ):
            return None
        camera_name = integration_name[ len( prefix ): ]
        if not camera_name:
            return None

        source_url = FrigateManager().get_camera_snapshot_url(
            camera_name = camera_name,
        )
        if source_url is None:
            return None
        return VideoSnapshot(
            source_url = source_url,
            metadata = { 'camera_name': camera_name },
        )

    def get_sensor_response_event_snapshot_url(
            self,
            sensor_response : SensorResponse,
    ) -> Optional[ str ]:
        """Per-event snapshot URL for a Frigate SensorResponse. Pulls
        the event_id from ``correlation_id`` and builds the URL fresh
        each call so operator-side base_url changes auto-heal every
        historical row."""
        if not sensor_response.has_event_video_snapshot:
            return None
        event_id = sensor_response.correlation_id
        if not event_id:
            return None
        return FrigateManager().get_event_snapshot_url( event_id = event_id )

    def get_sensor_response_video_stream(
            self,
            sensor_response : SensorResponse,
    ) -> Optional[ VideoStream ]:
        """Event-clip MP4 URL for a Frigate SensorResponse.
        Returns ``None`` when the response carries no clip
        (``has_event_video_clip`` False), when the
        ``correlation_id`` — Frigate's event_id — is absent, or when
        the integration client isn't ready."""
        if not sensor_response.has_event_video_clip:
            return None
        event_id = sensor_response.correlation_id
        if not event_id:
            return None
        source_url = FrigateManager().get_event_clip_url( event_id = event_id )
        if source_url is None:
            return None
        return VideoStream(
            stream_type = VideoStreamType.MP4,
            source_url = source_url,
            metadata = { 'event_id': event_id },
        )
