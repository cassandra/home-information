import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_controller import IntegrationController
from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.transient_models import IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .zm_controller import ZoneMinderController
from .zm_metadata import ZmMetaData
from .monitors import ZoneMinderMonitor
from . import views

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway ):

    def get_meta_data(self) -> IntegrationMetaData:
        return ZmMetaData

    def get_sensor_monitor(self) -> PeriodicMonitor:
        return ZoneMinderMonitor()
    
    def get_controller(self) -> IntegrationController:
        return ZoneMinderController()
    
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.ZmEnableView().get( request )
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.ZmDisableView().get( request )
