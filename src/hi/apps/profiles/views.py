import logging
from django.http import HttpRequest, HttpResponse, Http404
from django.urls import reverse
from django.views.generic import View

from hi.enums import ViewMode
from hi.hi_async_view import HiModalView

import hi.apps.common.antinode as antinode
from hi.apps.location.edit.views import LocationAddFirstView

from .profile_manager import ProfileManager, ProfileLoadNotAllowedError
from .enums import ProfileType
from .session_helpers import (
    mark_profile_initialized,
    mark_first_location_created,
    dismiss_view_intro_help,
)

logger = logging.getLogger(__name__)


class InitializeCustomView(View):

    def get(self, request, *args, **kwargs):
        # Create actions need edit ability.
        request.view_parameters.view_mode = ViewMode.EDIT
        request.view_parameters.to_session( request )

        response = LocationAddFirstView().get( request, *args, **kwargs )
        mark_first_location_created( request )
        return response

    
class InitializePredefinedView(View):
    
    def post( self, request: HttpRequest, profile_type: str ) -> HttpResponse:
        """
        Handle POST request to initialize database with selected profile.
        
        This view should only be accessible when the database is empty
        (no LocationView objects exist).
        """
        try:
            profile_enum = ProfileType.from_name(profile_type)
        except ValueError:
            raise Http404( f'Invalid profile type: {profile_type}' )
        
        profile_manager = ProfileManager()
        try:
            profile_manager.load_profile( profile_enum )
            logger.info( f'Successfully loaded profile: {profile_enum}' )

            mark_profile_initialized(request)

            request.view_parameters.view_mode = ViewMode.MONITOR
            request.view_parameters.to_session( request )

            return antinode.redirect_response( reverse('home') )

        except ProfileLoadNotAllowedError:
            # Entities or locations already exist (e.g. a direct POST that
            # bypassed the start gate). Don't build a profile on top of
            # existing data; defer to StartView, the canonical authority on
            # provisioning state, to route appropriately.
            logger.warning( 'Profile load attempted when not allowed; deferring to start.' )
            return antinode.redirect_response( reverse('start') )

        except Exception as e:
            # Genuine load failure on a loadable system (e.g. bad profile
            # JSON). The user can't fix a system issue, so fall back to the
            # manual setup flow.
            logger.error( f'Failed to load profile {profile_enum}: {e}' )
            return antinode.redirect_response( reverse('profiles_initialize_custom') )


class ViewReferenceHelpView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'profiles/modals/view_reference_help.html'

    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )


class DismissViewIntroHelpView( View ):

    def post( self, request, *args, **kwargs ):
        dismiss_view_intro_help( request )
        redirect_url = reverse( 'home' )
        return antinode.redirect_response( redirect_url )


class EditReferenceHelpView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'profiles/modals/edit_reference_help.html'

    def get( self, request, *args, **kwargs ):
        return self.modal_response( request )
    
