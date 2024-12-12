import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_controller import IntegrationController
from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.transient_models import IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .hass_controller import HassController
from .hass_metadata import HassMetaData
from .monitors import HassMonitor
from . import views

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def get_meta_data(self) -> IntegrationMetaData:
        return HassMetaData

    def get_monitor(self) -> PeriodicMonitor:
        return HassMonitor()
    
    def get_controller(self) -> IntegrationController:
        return HassController()
    
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassEnableView().get( request )
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassDisableView().get( request )
