import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.transient_models import IntegrationControlResult, IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .hass_metadata import HassMetaData
from .hass_monitor import HassMonitor
from . import views

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def get_meta_data(self) -> IntegrationMetaData:
        return HassMetaData

    def get_monitor(self) -> PeriodicMonitor:
        return HassMonitor()
    
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassEnableView().get( request )
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassDisableView().get( request )
    
    def sensor_response_details_view( self,
                                      request      : HttpRequest,
                                      details_str  : str ) -> HttpResponse:
        return views.SensorResponseDetailsView().get(
            request,
            details_str = details_str,
        )

    def do_control( self,
                    controller_integration_key  : IntegrationKey,
                    control_value               : str             ) -> IntegrationControlResult:

        # zzz Needs implementation


        return IntegrationControlResult()
