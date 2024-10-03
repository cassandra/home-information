import json
from typing import Dict

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax


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

    if force_json or ( request.META.get('HTTP_ACCEPT', '') == 'application/json' ):
        data = { 'error_message': context.get( 'message', 'Error (details missing).' ) }
        return HttpResponse( json.dumps( data ),
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
