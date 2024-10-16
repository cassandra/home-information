import json
import logging

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.edit.async_views import CollectionPositionEditView
from hi.apps.collection.models import Collection
import hi.apps.common.antinode as antinode
from hi.apps.entity.edit.async_views import EntityPositionEditView
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.enums import ItemType
from hi.hi_async_view import HiSideView

from . import forms

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class LocationEditView( View ):

    def post( self, request, *args, **kwargs ):
        location_id = kwargs.get('location_id')
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            raise Http404( request )

        location_edit_form = forms.LocationEditForm(
            request.POST,
            instance = location,
        )
        location_attribute_formset = forms.LocationAttributeFormset(
            request.POST,
            instance = location,
        )

        context = {
            'location': location,
            'location_edit_form': location_edit_form,
            'location_attribute_formset': location_attribute_formset,
        }
        
        if ( not location_edit_form.is_valid()
             or not location_attribute_formset.is_valid() ):
            template = get_template( 'location/edit/panes/location_edit.html' )
            content = template.render( context, request = request )
            return antinode.response(
                insert_map = {
                    DIVID['LOCATION_EDIT_PANE']: content,
                },
            )

        with transaction.atomic():
            location_edit_form.save()
            location_attribute_formset.save()

        return antinode.refresh_response()
            
    
@method_decorator( edit_required, name='dispatch' )
class LocationViewManageItemsView( HiSideView ):

    def get_template_name( self ) -> str:
        return 'location/edit/panes/location_view_manage_items.html'

    def get_template_context( self, request, *args, **kwargs ):

        location_view = request.view_parameters.location_view
        location_manager = LocationManager()
        entity_view_group_list = location_manager.create_entity_view_group_list(
            location_view = location_view,
        )
        collection_view_group = location_manager.create_collection_view_group(
            location_view = location_view,
        )
        return {
            'entity_view_group_list': entity_view_group_list,
            'collection_view_group': collection_view_group,
        }


@method_decorator( edit_required, name='dispatch' )
class LocationViewReorder( View ):
    
    def post(self, request, *args, **kwargs):
        try:
            location_view_id_list = json.loads( kwargs.get( 'location_view_id_list' ) )
        except Exception as e:
            raise BadRequest( str(e) )

        if not location_view_id_list:
            raise BadRequest( 'Missing location view ids.' )

        LocationManager().set_location_view_order(
            location_view_id_list = location_view_id_list,
        )            
        return antinode.response( main_content = 'OK' )        

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewEditView( View ):

    def post( self, request, *args, **kwargs ):

        location_view_id = kwargs.get('location_view_id')
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            raise Http404( request )

        location_view_edit_form = forms.LocationViewEditForm( request.POST, instance = location_view )
        if not location_view_edit_form.is_valid():
            context = {
                'location_view': location_view,
                'location_view_edit_form': location_view_edit_form,
            }
            template = get_template( 'location/edit/panes/location_view_edit.html' )
            content = template.render( context, request = request )
            return antinode.response(
                insert_map = {
                    DIVID['LOCATION_VIEW_EDIT_PANE']: content,
                },
            )
        
        location_view_edit_form.save()     
        return antinode.refresh_response()

    
class LocationViewGeometryView( View ):

    def post(self, request, *args, **kwargs):

        location_view_id = kwargs.get('location_view_id')
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            raise Http404( request )

        location_view_geometry_form = forms.LocationViewGeometryForm( request.POST, instance = location_view )
        if location_view_geometry_form.is_valid():
            location_view_geometry_form.save()
        else:
            logger.warning( 'LocationView geometry form is invalid.' )
            
        location_view_edit_form = forms.LocationViewEditForm( instance = location_view )

        context = {
            'location_view': location_view,
            'location_view_edit_form': location_view_edit_form,
        }
        template = get_template( 'location/edit/panes/location_view_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['LOCATION_VIEW_EDIT_PANE']: content,
            },
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewEntityToggleView( View ):

    def post( self, request, *args, **kwargs ):

        location_view_id = kwargs.get('location_view_id')
        entity_id = kwargs.get('entity_id')

        entity = Entity.objects.get( id = entity_id )
        location_view = LocationView.objects.get( id = location_view_id )
        exists_in_view = LocationManager().toggle_entity_in_view(
            entity = entity,
            location_view = location_view,
        )
            
        context = {
            'location_view': location_view,
            'entity': entity,
            'exists_in_view': exists_in_view,
        }
        template = get_template( 'location/edit/panes/location_view_entity_toggle.html' )
        main_content = template.render( context, request = request )

        location_view_data = LocationManager().get_location_view_data(
            location_view = location_view,
        )
        context = {
            'location_view_data': location_view_data,
        }
        template = get_template( 'location/location_view.html' )
        location_view_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : location_view_content,
            },
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewCollectionToggleView( View ):

    def post(self, request, *args, **kwargs):

        location_view_id = kwargs.get('location_view_id')
        collection_id = kwargs.get('collection_id')

        collection = Collection.objects.get( id = collection_id )
        location_view = LocationView.objects.get( id = location_view_id )
        exists_in_view = LocationManager().toggle_collection_in_view(
            collection = collection,
            location_view = location_view,
        )
            
        context = {
            'location_view': location_view,
            'collection': collection,
            'exists_in_view': exists_in_view,
        }
        template = get_template( 'location/edit/panes/location_view_collection_toggle.html' )
        main_content = template.render( context, request = request )

        location_view_data = LocationManager().get_location_view_data(
            location_view = location_view,
        )
        context = {
            'location_view_data': location_view_data,
        }
        template = get_template( 'location/location_view.html' )
        location_view_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : location_view_content,
            },
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationItemPositionView( View ):

    def post(self, request, *args, **kwargs):
        
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            return EntityPositionEditView().post(
                request,
                entity_id = item_id,
            )
        elif item_type == ItemType.COLLECTION:
            return CollectionPositionEditView().post(
                request,
                collection_id = item_id,
            )
        else:
            raise BadRequest( f'Cannot set item position for "{item_type}"' )


@method_decorator( edit_required, name='dispatch' )
class LocationItemPathView( View ):

    def post(self, request, *args, **kwargs):
        
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( 'Bad item id.' )

        svg_path_str = request.POST.get('svg_path')
        if not svg_path_str:
            raise BadRequest( 'Missing SVG path' )
        
        location_view = request.view_parameters.location_view
        if item_type == ItemType.ENTITY:
            EntityManager().set_entity_path(
                entity_id = item_id,
                location = location_view.location,
                svg_path_str = svg_path_str,
            )
        elif item_type == ItemType.COLLECTION:
            CollectionManager().set_collection_path(
                collection_id = item_id,
                location = location_view.location,
                svg_path_str = svg_path_str,
            )
        else:
            raise BadRequest( f'Cannot set SVG path for "{item_type}"' )

        return antinode.response(
            main_content = 'OK',
        )


    
    
