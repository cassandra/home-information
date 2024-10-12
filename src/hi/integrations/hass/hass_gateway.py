import logging

from django.http import HttpRequest, HttpResponse

from hi.integrations.core.integration_gateway import IntegrationGateway

from . import views

logger = logging.getLogger(__name__)


class HassGateway( IntegrationGateway ):

    def enable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassEnableView().post( request )
    
    def disable_modal_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:
        return views.HassDisableView().post( request )

    def manage_pane_view( self, request : HttpRequest, *args, **kwargs ) -> HttpResponse:

        post_action = request.POST.get('action')
        if post_action == 'sync':
            return views.HassSyncView().post( request, *args, **kwargs )
            
        return views.HassManageView().get( request, *args, **kwargs )
    
    
