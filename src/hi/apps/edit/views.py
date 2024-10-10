import json
import logging
import re

from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.common.antinode as antinode
import hi.apps.collection.edit.views as collection_edit_views
from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.entity.entity_manager import EntityManager
import hi.apps.location.edit.views as location_edit_views
from hi.apps.location.forms import LocationItemPositionForm
from hi.decorators import edit_required
from hi.hi_grid_view import HiGridView
from hi.enums import ItemType
from hi.views import bad_request_response

from hi.enums import ViewMode

logger = logging.getLogger(__name__)


class EditStartView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.
        
        request.view_parameters.view_mode = ViewMode.EDIT
        request.view_parameters.to_session( request )

        redirect_url = request.META.get('HTTP_REFERER')
        if not redirect_url:
            redirect_url = reverse('home')
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class EditEndView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.

        request.view_parameters.view_mode = ViewMode.MONITOR
        request.view_parameters.to_session( request )

        redirect_url = request.META.get('HTTP_REFERER')
        if not redirect_url:
            redirect_url = reverse('home')
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class EditDeleteView( View ):

    def get(self, request, *args, **kwargs):

        if request.view_parameters.view_type.is_location_view:
            return location_edit_views.LocationViewDeleteView().get(
                request,
                location_view_id = request.view_parameters.location_view_id,
            )

        if request.view_parameters.view_type.is_collection:
            return collection_edit_views.CollectionDeleteView().get(
                request,
                collection_id = request.view_parameters.collection_id,
            )
            
        else:
            return bad_request_response( request,
                                         message = f'Bad view type "{request.view_parameters.view_type}".' )

    
@method_decorator( edit_required, name='dispatch' )
class EditLocationItemPositionView( View ):

    def post(self, request, *args, **kwargs):
        
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            return bad_request_response( request, messahe = 'Bad item id.' )
        
        location_view = request.view_parameters.location_view
        if item_type == ItemType.ENTITY:
            svg_position_model = EntityManager().get_entity_position(
                entity_id = item_id,
                location = location_view.location,
            )
        elif item_type == ItemType.COLLECTION:
            svg_position_model = CollectionManager().get_collection_position(
                collection_id = item_id,
                location = location_view.location,
            )
        else:
            return bad_request_response( request, message = f'Cannot set SVG position for "{item_type}"' )

        location_item_position_form = LocationItemPositionForm(
            request.POST,
            item_html_id = svg_position_model.svg_icon_item.html_id,
        )
        if location_item_position_form.is_valid():
            location_item_position_form.to_svg_position_model( svg_position_model )
            svg_position_model.save()

        svg_icon_item = svg_position_model.svg_icon_item            
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
class EditLocationItemPathView( View ):

    def post(self, request, *args, **kwargs):
        
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            return bad_request_response( request, messahe = 'Bad item id.' )

        svg_path_str = request.POST.get('svg_path')
        if not svg_path_str:
            return bad_request_response( request, message = 'Missing SVG path' )
        
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
            return bad_request_response( request, message = f'Cannot set SVG path for "{item_type}"' )

        return antinode.response(
            main_content = 'OK',
        )


@method_decorator( edit_required, name='dispatch' )
class AddRemoveView( HiGridView ):

    def get( self, request, *args, **kwargs ):

        if request.view_parameters.view_type.is_location_view:
            return location_edit_views.LocationViewAddRemoveItemView().get( request, *args, **kwargs )

        if request.view_parameters.view_type.is_collection:
            return collection_edit_views.CollectionAddRemoveItemView().get( request, *args, **kwargs )

        context = {
        }
        return self.side_panel_response(
            request = request,
            template_name = 'edit/panes/default.html',
            context = context,
        )

    
@method_decorator( edit_required, name='dispatch' )
class ReorderItemsView( View ):

    def post( self, request, *args, **kwargs ):
        try:
            item_type_id_list = ItemType.parse_list_from_dict( request.POST )
        except ValueError as e:
            return bad_request_response( request, message = str(e) )

        try:
            item_types = set()
            item_id_list = list()
            for item_type, item_id in item_type_id_list:
                item_types.add( item_type )
                item_id_list.append( item_id )
                continue
        except ValueError as ve:
            return bad_request_response( request, message = str(ve) )
            
        if len(item_types) < 1:
            return bad_request_response( request, message = 'No ids found' )

        if len(item_types) > 1:
            return bad_request_response( request, message = f'Too many item types: {item_types}' )

        item_type = next(iter(item_types))
        if item_type == ItemType.ENTITY:
            if not request.view_parameters.view_type.is_collection:
                return bad_request_response( request, message = 'Entity reordering for collections only.' )
            return collection_edit_views.CollectionReorderEntitiesView().post(
                request,
                collection_id = request.view_parameters.collection_id,
                entity_id_list = json.dumps( item_id_list ),
            )

        elif item_type == ItemType.COLLECTION:
            return collection_edit_views.CollectionReorder().post(
                request,
                collection_id_list = json.dumps( item_id_list ),
            )

        elif item_type == ItemType.LOCATION_VIEW:
            return location_edit_views.LocationViewReorder().post(
                request,
                location_view_id_list = json.dumps( item_id_list ),
            )

        else:
            return bad_request_response( request, message = f'Unknown item type: {item_type}' )
