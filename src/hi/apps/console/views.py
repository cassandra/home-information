from django.http import JsonResponse

from hi.hi_async_view import HiModalView

from .constants import ConsoleConstants


class ConsoleLockView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'console/modals/console_unlock.html'

    def post( self, request, *args, **kwargs ):
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = True
        context = {
        }
        return self.modal_response( request, context )

    
class ConsoleUnlockView( ConsoleLockView ):

    def get( self, request, *args, **kwargs ):
        context = {
        }
        return self.modal_response( request, context )
    
    def post(self, request, *args, **kwargs):

        # N.B. Simplified security for now. Just meant to be used when
        # visitors in the house to prevent snooping. Beef up security here
        # if/when needed.
        
        request.session[ConsoleConstants.CONSOLE_LOCKED_SESSION_VAR] = False
        return JsonResponse( {'message': 'Console unlocked.'} )
