from django.core.exceptions import BadRequest
from django.shortcuts import render
from django.views.generic import View

from .enums import SecurityStateAction
from .security_manager import SecurityManager


class SecurityStateActionView( View ):

    def get( self, request, *args, **kwargs ):
        action_str = kwargs.get( 'action' )
        try:
            security_state_action = SecurityStateAction.from_name( action_str )
        except ValueError:
            raise BadRequest( 'Bad action value.' )

        security_manager = SecurityManager()
        security_manager.set_security_state( security_state_action = security_state_action )

        context = {
            'security_status_data': security_manager.get_security_status_data(),
        }
        return render( request, 'security/panes/security_state_control.html', context )
