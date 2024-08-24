import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_gateway import IntegrationGateway

from . import views

logger = logging.getLogger(__name__)


class ZoneMinderGateway( IntegrationGateway ):

    def enable( self, request : HttpRequest ) -> HttpResponse:
        return views.ZmEnableView().post( request )
    
    def disable( self, request : HttpRequest ) -> HttpResponse:
        return views.ZmDisableView().post( request )

    def manage( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:

        post_action = request.POST.get('action')
        if post_action == 'sync':
            return views.ZmSyncView().post( request, *args, **kwargs )
            
        return views.ZmManageView().get( request, *args, **kwargs )
    
    
