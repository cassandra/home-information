from functools import wraps
import logging

from . import views

logger = logging.getLogger( __name__ )


def edit_required(func):
    """
    Decorator used for views that require an autheticated user with an email.
    """
    @wraps(func)
    def wrapper( request, *args, **kwargs):
        if not request.view_parameters.view_mode.is_editing:
            return views.edit_required_response( request )
        return func( request, *args, **kwargs )
    
    return wrapper
