import logging

from hi.integrations.integration_controller import IntegrationController
from hi.integrations.integration_gateway import IntegrationGateway
from hi.integrations.integration_manage_view_pane import IntegrationManageViewPane
from hi.integrations.transient_models import IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .hass_controller import HassController
from .hass_manage_view_pane import HassManageViewPane
from .hass_metadata import HassMetaData
from .monitors import HassMonitor

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def get_metadata(self) -> IntegrationMetaData:
        return HassMetaData

    def get_manage_view_pane(self) -> IntegrationManageViewPane:
        return HassManageViewPane()

    def get_monitor(self) -> PeriodicMonitor:
        return HassMonitor()
    
    def get_controller(self) -> IntegrationController:
        return HassController()
