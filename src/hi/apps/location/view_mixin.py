from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest
from django.template.loader import get_template

import hi.apps.common.antinode as antinode
import hi.apps.location.edit.forms as forms
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView

from hi.constants import DIVID


class LocationViewMixin:

    def get_location( self, request, *args, **kwargs ) -> Location:
        """ Assumes there is a required location_id in kwargs """
        try:
            location_id = int( kwargs.get( 'location_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location id.' )
        try:
            return LocationManager().get_location(
                request = request,
                location_id = location_id,
            )
        except Location.DoesNotExist:
            raise Http404( request )
 
    def get_location_view( self, request, *args, **kwargs ) -> LocationView:
        """ Assumes there is a required location_view_id in kwargs """
        try:
            location_view_id = int( kwargs.get( 'location_view_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location_view id.' )
        try:
            return LocationManager().get_location_view(
                request = request,
                location_view_id = location_view_id,
            )
        except LocationView.DoesNotExist:
            raise Http404( request )
           
    def location_edit_response( self,
                                request                         : HttpRequest,
                                location                        : Location,
                                location_edit_form              : forms.LocationEditForm             = None,
                                location_attribute_formset      : forms.LocationAttributeFormSet     = None,
                                location_attribute_upload_form  : forms.LocationAttributeUploadForm  = None,
                                status_code                     : int                                = 200 ):

        if not location_edit_form:
            location_edit_form = forms.LocationEditForm(
                instance = location,
            )
        if not location_attribute_formset:
            location_attribute_formset = forms.LocationAttributeFormSet(
                instance = location,
                prefix = f'location-{location.id}',
                form_kwargs = {
                    'show_as_editable': True,
                },
            )
        if not location_attribute_upload_form:
            location_attribute_upload_form = forms.LocationAttributeUploadForm(
                request.POST,
                instance = location,
            )    
        
        context = {
            'location': location,
            'location_edit_form': location_edit_form,
            'location_attribute_formset': location_attribute_formset,
            'location_attribute_upload_form': location_attribute_upload_form,
        }
        
        template = get_template( 'location/edit/panes/location_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['LOCATION_EDIT_PANE']: content,
            },
        )
