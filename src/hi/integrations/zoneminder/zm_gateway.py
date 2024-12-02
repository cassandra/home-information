import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.integration_key import IntegrationKey
from hi.integrations.core.transient_models import IntegrationControlResult, IntegrationMetaData
from hi.apps.monitor.periodic_monitor import PeriodicMonitor

from .zm_metadata import ZmMetaData
from .zm_monitor import ZoneMinderMonitor
from . import views

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway ):

    def get_meta_data(self) -> IntegrationMetaData:
        return ZmMetaData

    def get_monitor(self) -> PeriodicMonitor:
        return ZoneMinderMonitor()
    
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.ZmEnableView().get( request )
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.ZmDisableView().get( request )

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
