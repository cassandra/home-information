import logging
from django.http import HttpRequest, HttpResponse, Http404
from django.views.generic import View
from django.shortcuts import redirect

from hi.hi_async_view import HiModalView
from .profile_manager import ProfileManager
from .enums import ProfileType
from .session_helpers import mark_profile_initialized

logger = logging.getLogger(__name__)


class ProfilesInitializeView(View):
    
    def get( self, request: HttpRequest, profile_type: str ) -> HttpResponse:
        # GET requests should redirect back to start page
        # Profile initialization requires POST for database changes
        return redirect('start')
    
    def post( self, request: HttpRequest, profile_type: str ) -> HttpResponse:
        """
        Handle POST request to initialize database with selected profile.
        
        This view should only be accessible when the database is empty
        (no LocationView objects exist).
        """
        # Validate profile_type parameter - raise 404 for invalid URLs
        try:
            profile_enum = ProfileType.from_name(profile_type)
        except ValueError:
            raise Http404( f'Invalid profile type: {profile_type}' )
        
        profile_manager = ProfileManager()
        try:
            profile_manager.load_profile( profile_enum )
            logger.info( f'Successfully loaded profile: {profile_enum}' )
            
            # Mark profile as initialized for help system
            mark_profile_initialized(request)
            
            return redirect('home')
        except Exception as e:
            logger.error(f'Failed to load profile {profile_enum}: {e}')
            # Fall back to manual setup flow - user can't fix system issues
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
    
