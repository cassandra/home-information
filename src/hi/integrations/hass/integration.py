import logging

from hi.integrations.core.integration_controller import IntegrationController
from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.transient_models import IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .hass_controller import HassController
from .hass_metadata import HassMetaData
from .monitors import HassMonitor

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def get_metadata(self) -> IntegrationMetaData:
        return HassMetaData

    def get_monitor(self) -> PeriodicMonitor:
        return HassMonitor()
    
    def get_controller(self) -> IntegrationController:
        return HassController()
