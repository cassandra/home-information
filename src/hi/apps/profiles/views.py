import logging
from django.http import HttpRequest, HttpResponse
from django.views.generic import View
from django.shortcuts import redirect

from hi.hi_async_view import HiModalView

logger = logging.getLogger(__name__)


class ProfilesInitializeView(View):
    
    def get( self, request: HttpRequest, profile_type: str ) -> HttpResponse:
        # TODO: Implement profile application logic
        # For now, just redirect to location edit as placeholder
        return redirect('location_edit_location_add_first')


class ViewModeHelpView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'profiles/modals/view_mode_help.html'

    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )


class EditModeHelpView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'profiles/modals/edit_mode_help.html'

    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )
    
