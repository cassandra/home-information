import logging

from django.views.generic import View

from .view_mixin import ControlViewMixin

logger = logging.getLogger(__name__)


class ControllerDiscreteView( View, ControlViewMixin ):

    def post( self, request, *args, **kwargs ):
        controller = self.get_controller( request, *args, **kwargs )
        value = request.POST.get( 'value' )
        logger.debug( f'Setting discrete controller = "{value}"' )


        # zzz Sanity check value is in value_range


        # zzz Check against latest state value????

        
        error_messages = list()



        return self.controller_data_response(
            request = request,
            controller = controller,
            error_messages = error_messages,
        )

    
class ControllerOnOffView( View, ControlViewMixin ):

    def post( self, request, *args, **kwargs ):
        controller = self.get_controller( request, *args, **kwargs )
        
        value = request.POST.get( 'value' )
        logger.debug( f'Setting on-off controller = "{value}"' )




        # zzz Sanity check value is in value_range


        # zzz Check against latest state value????

        



        
        error_messages = list()



        return self.controller_data_response(
            request = request,
            controller = controller,
            error_messages = error_messages,
        )
