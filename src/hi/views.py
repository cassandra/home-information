import json
from typing import Dict

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.healthcheck import do_healthcheck
from hi.apps.common.utils import is_ajax
from hi.apps.profiles.profile_manager import ProfileManager

from hi.apps.profiles.enums import ProfileType
from hi.enums import ProvisioningState


def error_response( request             : HttpRequest,
                    sync_template_name  : str,
                    async_template_name : str,
                    status_code         : int,
                    force_json          : bool              = False,
                    context             : Dict[ str, str ]  = None ):
    """
    Helper routine for the similar error response functions.
    """
    if context is None:
        context = {}

    if 'error_message' not in context:
        context['error_message'] = 'Error (details missing).'
    if 'message' in context:
        context['error_message'] = context['message']
        
    if force_json or ( request.headers.get('accept', '') == 'application/json' ):
        return HttpResponse( json.dumps( context ),
                             content_type = "application/json",
                             status = status_code )
    
    if is_ajax( request ):
        response = antinode.modal_from_template( request,
                                                 async_template_name,
                                                 context )
    else:
        response = render( request, sync_template_name, context )
        
    response.status_code = status_code
    return response


def bad_request_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Bad request.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/bad_request.html",
                           async_template_name = "modals/bad_request.html",
                           status_code = 400,
                           force_json = force_json,
                           context = context )


def improperly_configured_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Improperly configured.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/improperly_configured.html",
                           async_template_name = "modals/improperly_configured.html",
                           status_code = 501,
                           force_json = force_json,
                           context = context )


def not_authorized_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Not authorized.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/not_authorized.html",
                           async_template_name = "modals/not_authorized.html",
                           status_code = 403,
                           force_json = force_json,
                           context = context )


def method_not_allowed_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Method not allowed.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/method_not_allowed.html",
                           async_template_name = "modals/method_not_allowed.html",
                           status_code = 405,
                           force_json = force_json,
                           context = context )


def page_not_found_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Page not found.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/page_not_found.html",
                           async_template_name = "modals/page_not_found.html",
                           status_code = 404,
                           force_json = force_json,
                           context = context )


def internal_error_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Internal error.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/internal_error.html",
                           async_template_name = "modals/internal_error.html",
                           status_code = 500,
                           force_json = force_json,
                           context = context )


def transient_error_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Transient error.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/transient_error.html",
                           async_template_name = "modals/transient_error.html",
                           status_code = 503,
                           force_json = force_json,
                           context = context )


def custom_404_handler( request, exception):
    return HttpResponseNotFound( page_not_found_response( request ))     


def edit_required_response( request, message : str = None, force_json : bool = False ):
    if not message:
        message = 'Edit mode is required for this request.'
    context = { 'message': message }
    return error_response( request = request,
                           sync_template_name = "pages/edit_required.html",
                           async_template_name = "modals/edit_required.html",
                           status_code = 200,  # Needed for PWA (not 403)
                           force_json = force_json,
                           context = context )


def home_javascript_files( request, filename ):
    return render(request, filename, {}, content_type = "text/javascript")

    
class HealthView( View ):
    
    def get(self, request, *args, **kwargs):
        status_dict = do_healthcheck()
        response_status = 200 if status_dict['is_healthy'] else 500
        return JsonResponse( {'status': status_dict }, status=response_status)


class HomeView( View ):

    def get(self, request, *args, **kwargs):

        # Hot path: assume the system is provisioned and route straight to
        # the relevant default view, adding no provisioning queries here.
        # The rare non-provisioned states (no location) are detected and
        # handled downstream by LocationViewDefaultView, which resolves the
        # provisioning state only when it actually finds nothing to show.
        if request.view_parameters.view_type.is_collection:
            redirect_url = reverse( 'collection_view_default' )
        else:
            redirect_url = reverse( 'location_view_default' )
        query_string = request.META.get( 'QUERY_STRING', '' )
        if query_string:
            redirect_url = redirect_url + '?' + query_string
        return HttpResponseRedirect( redirect_url )


class SetSnapGridView( View ):
    """Persist the SVG-editor snap-grid preference (screen pixels) to the
    session view parameters so it survives reloads. Both SVG editors post
    here on change. Value is clamped to the same range as the UI input
    (0 = snapping disabled); malformed input is rejected."""

    MIN_PIXELS = 0
    MAX_PIXELS = 50

    def post( self, request, *args, **kwargs ):
        try:
            value = int( request.POST.get( 'snap_grid_pixels' ) )
        except ( TypeError, ValueError ):
            return antinode.response( status = 400 )
        value = max( self.MIN_PIXELS, min( value, self.MAX_PIXELS ) )
        request.view_parameters.svg_snap_grid_pixels = value
        request.view_parameters.to_session( request )
        return antinode.response( status = 200 )


class StartView( View ):

    def get(self, request, *args, **kwargs):

        # StartView is the canonical place that defines policy for the
        # ProvisioningState. Any view that requires a particular state but
        # finds it unmet (e.g. LocationViewDefaultView with no location)
        # simply redirects here and lets this view decide what to do:
        #   PROVISIONED       -> nothing to set up; go home.
        #   REQUIRES_LOCATION -> data exists but no location; add one.
        #   ALLOWS_PROFILE    -> render the profile picker (below).
        state = ProfileManager().get_provisioning_state()
        if state == ProvisioningState.PROVISIONED:
            return HttpResponseRedirect( reverse( 'home' ) )
        if state == ProvisioningState.REQUIRES_LOCATION:
            return HttpResponseRedirect( reverse( 'profiles_initialize_custom' ) )

        # Define which profiles to show and in what order
        # This allows us to control which profiles appear on the start page
        # and their display order, independent of enum definition order
        profile_type_list = [
            ProfileType.SINGLE_STORY,
            ProfileType.TWO_STORY,
            ProfileType.APARTMENT,
        ]

        context = {
            'profile_type_list': profile_type_list,
        }
        return render( request, 'pages/start.html', context )


class ManifestView( View ):

    def get(self, request, *args, **kwargs):
        """
        Serves the PWA manifest.json for full screen mode support.
        Configured for landscape orientation (tablet primary use case).
        """
        return render(request, 'manifest.json', {}, content_type="application/json")
    
