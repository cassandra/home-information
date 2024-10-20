import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_factory import IntegrationFactory
from hi.integrations.core.integration_gateway import IntegrationGateway
from hi.integrations.core.transient_models import IntegrationMetaData

from .hass_metadata import HassMetaData
from . import views

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def get_meta_data(self) -> IntegrationMetaData:
        return HassMetaData
    
    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassEnableView().get( request )
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassDisableView().get( request )
    
    
IntegrationFactory().register( HassGateway() )
