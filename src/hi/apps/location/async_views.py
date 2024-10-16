import logging

from django.core.exceptions import BadRequest
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

from hi.apps.collection.async_views import CollectionDetailsView
from hi.apps.entity.async_views import EntityDetailsView
from hi.apps.location.edit.forms import (
    LocationAttributeFormset,
    LocationEditForm,
    LocationViewEditForm,
)

from hi.enums import ItemType
from hi.hi_async_view import HiSideView

from .location_manager import LocationManager

from .models import LocationView

logger = logging.getLogger(__name__)


class LocationViewDetailsView( HiSideView ):

    def get_template_name( self ) -> str:
        return 'location/panes/location_details.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        try:
            location_view_id = int( kwargs.get( 'location_view_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location view id.' )
        try:
            location_view = LocationManager().get_location_view(
                request = request,
                location_view_id = location_view_id,
            )
        except LocationView.DoesNotExist:
            raise Http404( request )

        return {
            'location': location_view.location,
            'location_edit_form': LocationEditForm( instance = location_view.location ),
            'location_attribute_formset': LocationAttributeFormset(
                instance = location_view.location,
                form_kwargs = {
                    'is_editable': True,
                },
            ),
            'location_view': location_view,
            'location_view_edit_form': LocationViewEditForm(  instance = location_view ),
        }


class LocationItemDetailsViewNEW( HiSideView ):

    def dispatch( self, request, *args, **kwargs ):
        try:
            self._item_type, self._item_id = ItemType.parse_from_dict( kwargs )
            if self._item_type == ItemType.ENTITY:
                self._view = EntityDetailsView()
                self._kwargs = { 'entity_id': self._item_id }
            elif self._item_type == ItemType.COLLECTION:
                self._view = CollectionDetailsView()
                self._kwargs = { 'collection_id': self._item_id }
            else:
                raise BadRequest( 'Unsupported item type.' )
                  
        except ValueError:
            raise BadRequest( 'Bad item id.' )
        
        return super().dispatch( request, *args, **kwargs )
     
    def get_template_name( self ) -> str:
        return self._view.get_template_name()

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        return self._view.get_template_context( request, **self._kwargs )

    
class LocationItemDetailsView( View ):

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( request, message = 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            redirect_url = reverse( 'entity_details', kwargs = { 'entity_id': item_id } )
            return HttpResponseRedirect( redirect_url )
            return EntityDetailsView().get(
                request = request,
                entity_id = item_id,
            )            
    
        if item_type == ItemType.COLLECTION:
            redirect_url = reverse( 'collection_details', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( redirect_url )
            return CollectionDetailsView().get(
                request = request,
                collection_id = item_id,
            )            

        raise BadRequest( 'Unknown item type "{item_type}".' )



        
    
