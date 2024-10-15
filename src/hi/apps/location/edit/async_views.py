from decimal import Decimal
import json
import logging

from django.core.exceptions import BadRequest
from django.http import Http404
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection
import hi.apps.common.antinode as antinode
from hi.apps.common.svg_models import SvgViewBox
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity
from hi.apps.location.forms import LocationItemPositionForm
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.enums import ItemType
from hi.hi_async_view import HiSideView

from . import forms

logger = logging.getLogger(__name__)


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
class LocationEditView( View ):

    def post( self, request, *args, **kwargs ):
        raise NotImplementedError()

    
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

        try:
            svg_view_box_str = request.POST.get('view_box')
            svg_view_box = SvgViewBox.from_attribute_value( svg_view_box_str )
        except (TypeError, ValueError ):
            raise BadRequest( f'Bad viewbox: {svg_view_box_str}' )

        try:
            svg_rotate_angle = float( request.POST.get('rotate_angle'))
        except (TypeError, ValueError ):
            raise BadRequest( f'Bad rotate angle: {svg_rotate_angle}' )

        location_view.svg_view_box_str = str(svg_view_box)
        location_view.svg_rotate = Decimal( svg_rotate_angle )
        location_view.save()

        return antinode.response( main_content = 'OK' )

    
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
        
        location_view = request.view_parameters.location_view
        if item_type == ItemType.ENTITY:
            location_item_position_model = EntityManager().get_entity_position(
                entity_id = item_id,
                location = location_view.location,
            )
        elif item_type == ItemType.COLLECTION:
            location_item_position_model = CollectionManager().get_collection_position(
                collection_id = item_id,
                location = location_view.location,
            )
        else:
            raise BadRequest( f'Cannot set SVG position for "{item_type}"' )

        location_item_position_form = LocationItemPositionForm(
            request.POST,
            item_html_id = location_item_position_model.location_item.html_id,
        )
        if location_item_position_form.is_valid():
            location_item_position_form.to_location_item_position_model( location_item_position_model )
            location_item_position_model.save()

        svg_icon_item = SvgItemFactory().create_svg_icon_item(
            item = location_item_position_model.location_item,
            position = location_item_position_model,
        )
        
        context = {
            'location_item_position_form': location_item_position_form,
        }
        template = get_template('location/edit/panes/location_item_position.html')
        content = template.render( context, request = request )

        insert_map = {
            location_item_position_form.content_html_id: content,
        }
        set_attributes_map = {
            svg_icon_item.html_id: {
                'transform': svg_icon_item.transform_str,
            }
        }
        return antinode.response(
            insert_map = insert_map,
            set_attributes_map = set_attributes_map,
        )


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


    
    
