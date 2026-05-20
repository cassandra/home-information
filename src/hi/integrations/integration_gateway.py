from typing import List, Optional

from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import VideoSnapshot, VideoStream
from hi.apps.monitor.periodic_monitor import PeriodicMonitor
from hi.apps.sense.transient_models import SensorResponse
from hi.apps.system.health_status_provider import HealthStatusProvider

from .integration_controller import IntegrationController
from .integration_manage_view_pane import IntegrationManageViewPane
from .integration_synchronizer import IntegrationSynchronizer
from .models import IntegrationAttribute
from .transient_models import (
    ConnectionTestResult,
    IntegrationMetaData,
    IntegrationValidationResult,
)


class IntegrationGateway:
    """
    Each integration needs to provide an Integration Manager that implements these methods.
    """

    def get_metadata(self) -> IntegrationMetaData:
        raise NotImplementedError('Subclasses must override this method')

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        raise NotImplementedError('Subclasses must override this method')

    def get_monitor(self) -> PeriodicMonitor:
        raise NotImplementedError('Subclasses must override this method')

    def get_controller(self) -> IntegrationController:
        raise NotImplementedError('Subclasses must override this method')

    def notify_settings_changed(self):
        """
        This method is called when Integration or IntegrationAttribute models
        are modified. Each integration should implement this to reload its
        configuration and notify any dependent components.
        """
        raise NotImplementedError('Subclasses must override this method')

    def get_health_status_provider(self) -> HealthStatusProvider:
        raise NotImplementedError('Subclasses must override this method')

    def get_synchronizer(self) -> Optional[IntegrationSynchronizer]:
        """
        Return the integration's synchronizer when it supports sync;
        None otherwise. Sync is an opt-in capability — not every
        integration requires one. The framework owns the sync workflow
        (pre-sync confirmation, sync execution, post-sync placement);
        the synchronizer participates by providing the integration-
        specific work plus a small amount of peripheral metadata.

        The Issue #283 sync-check probe also rides on the synchronizer
        (see ``IntegrationSynchronizer.check_needs_sync``): integrations
        without a synchronizer naturally opt out of both full sync and
        the periodic drift check.
        """
        return None

    def validate_configuration(
            self,
            integration_attributes: List[IntegrationAttribute]
    ) -> IntegrationValidationResult:
        """
        Schema-only validation of the proposed configuration. Must NOT
        perform network operations. Returns success if the attribute set
        is structurally usable; returns an error otherwise. For live
        connection probing, see test_connection().
        """
        raise NotImplementedError('Subclasses must override this method')

    def test_connection(
            self,
            integration_attributes: List[IntegrationAttribute],
            timeout_secs: Optional[float],
    ) -> ConnectionTestResult:
        """
        Live connection probe against the proposed configuration. Must
        respect the bounded timeout. Used at attribute-save time
        (Configure / Reconfigure) and before relaunching monitors
        (Resume).
        """
        raise NotImplementedError('Subclasses must override this method')
    
    def get_entity_video_stream(self, entity: Entity) -> Optional[VideoStream]:
        return None

    def get_entity_video_snapshot(self, entity: Entity) -> Optional[VideoSnapshot]:
        return None

    def get_sensor_response_video_stream(
            self,
            sensor_response: SensorResponse) -> Optional[VideoStream]:
        return None

    def get_sensor_response_event_snapshot_url(
            self,
            sensor_response: SensorResponse) -> Optional[str]:
        """Return the URL to the per-event captured snapshot frame for
        a SensorResponse, or ``None`` when the integration cannot
        produce one. Generated at render time from the event id so the
        URL always reflects current integration configuration (e.g.,
        an operator who moves the upstream host doesn't get stale
        URLs on historical rows). Pair with
        ``SensorResponse.has_event_video_snapshot`` — only call when
        the flag is True."""
        return None
