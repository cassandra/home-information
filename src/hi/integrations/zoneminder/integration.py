import logging

from hi.integrations.core.integration_controller import IntegrationController
from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.core.transient_models import IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .zm_controller import ZoneMinderController
from .zm_manage_view_pane import ZmManageViewPane
from .zm_metadata import ZmMetaData
from .monitors import ZoneMinderMonitor

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway ):

    def get_metadata(self) -> IntegrationMetaData:
        return ZmMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return ZmManageViewPane()
    
    def get_monitor(self) -> PeriodicMonitor:
        return ZoneMinderMonitor()
    
    def get_controller(self) -> IntegrationController:
        return ZoneMinderController()
