import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.transient_models import IntegrationMetaData

from .zm_metadata import ZmMetaData
from . import views

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway ):

    def get_meta_data(self) -> IntegrationMetaData:
        return ZmMetaData
    
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.ZmEnableView().get( request )
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.ZmDisableView().get( request )
