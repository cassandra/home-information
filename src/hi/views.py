import json
from typing import Dict

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax
from hi.apps.location.edit.forms import LocationForm


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
        
    if force_json or ( request.META.get('HTTP_ACCEPT', '') == 'application/json' ):
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


class HomeView( View ):

    def get(self, request, *args, **kwargs):

        if request.view_parameters.view_type.is_collection:
            redirect_url = reverse( 'collection_view_default' )
        else:
            redirect_url = reverse( 'location_view_default' )
        return HttpResponseRedirect( redirect_url )

    
class StartView( View ):

    def get(self, request, *args, **kwargs):
        context = {
            'location_form': LocationForm(),
        }
        return render( request, 'pages/start.html', context )
