import json
import logging
import re
from typing import Dict

from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.common.antinode as antinode
import hi.apps.collection.edit.views as collection_edit_views
from hi.apps.collection.helpers import CollectionHelpers
import hi.apps.entity.edit.views as entity_edit_views
from hi.apps.entity.entity_manager import EntityManager
import hi.apps.location.edit.views as location_edit_views
from hi.apps.location.forms import SvgPositionForm
from hi.decorators import edit_required
from hi.views import bad_request_response

from hi.constants import DIVID
from hi.enums import ViewMode

logger = logging.getLogger(__name__)


class EditViewMixin:

    def parse_html_id( self, html_id : str ):
        m = re.match( r'^hi-([\w\-]+)-(\d+)$', html_id )
        if not m:
            raise ValueError( 'Bad html id "{html_id}".' )
        return ( m.group(1), int(m.group(2)) )

    def get_edit_side_panel_response( self,
                                      request        : HttpRequest,
                                      template_name  : str,
                                      context        : Dict  = None):
        if context is None:
            context = dict()
        template = get_template( template_name )
        content = template.render( context, request = request )
        insert_map = {
            DIVID['EDIT_ITEM']: content,
        }
        return antinode.response(
            insert_map = insert_map,
        )
        
    
class EditStartView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.
        
        if request.view_parameters.view_mode.is_editing:
            return bad_request_response( request, message = 'Edit mode already started.' )

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
class EditDetailsView( View, EditViewMixin ):

    def get(self, request, *args, **kwargs):

        html_id = kwargs.get('html_id')
        if not html_id:
            return self.get_default_details( request )
            
        ( item_type, item_id ) = self.parse_html_id( kwargs.get('html_id'))

        if item_type == 'entity':
            return entity_edit_views.EntityDetailsView().get(
                request = request,
                entity_id = item_id,
            )            

        if item_type == 'collection':
            return collection_edit_views.CollectionDetailsView().get(
                request = request,
                collection_id = item_id,
            )            

        return bad_request_response( request, message = 'Unknown item type "{item_type}".' )

    def get_default_details( self, request ):
        return self.get_edit_side_panel_response(
            request = request,
            template_name = 'edit/panes/default.html',
        )
        
                
@method_decorator( edit_required, name='dispatch' )
class EditSvgPositionView( View, EditViewMixin ):

    def post(self, request, *args, **kwargs):
        
        ( item_type, item_id ) = self.parse_html_id( kwargs.get('html_id'))

        location_view = request.view_parameters.location_view
        if item_type == 'entity':
            svg_position_model = EntityManager().get_entity_position(
                entity_id = item_id,
                location = location_view.location,
            )
        elif item_type == 'collection':
            svg_position_model = CollectionHelpers.get_collection_position(
                collection_id = item_id,
                location = location_view.location,
            )
        else:
            return bad_request_response( request, message = f'Cannot set SVG position for "{item_type}"' )

        svg_position_form = SvgPositionForm(
            request.POST,
            item_html_id = svg_position_model.svg_icon_item.html_id,
        )
        if svg_position_form.is_valid():
            svg_position_form.to_svg_position_model( svg_position_model )
            svg_position_model.save()

        svg_icon_item = svg_position_model.svg_icon_item            
        context = {
            'svg_position_form': svg_position_form,
        }
        template = get_template('edit/panes/svg_position.html')
        content = template.render( context, request = request )

        insert_map = {
            svg_position_form.content_html_id: content,
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
class EditSvgPathView( View, EditViewMixin ):

    def post(self, request, *args, **kwargs):
        
        ( item_type, item_id ) = self.parse_html_id( kwargs.get('html_id'))
        svg_path_str = request.POST.get('svg_path')
        if not svg_path_str:
            return bad_request_response( request, message = 'Missing SVG path' );
        
        location_view = request.view_parameters.location_view
        if item_type == 'entity':
            EntityManager().set_entity_path(
                entity_id = item_id,
                location = location_view.location,
                svg_path_str = svg_path_str,
            )
        else:
            return bad_request_response( request, message = f'Cannot set SVG path for "{item_type}"' )

        return antinode.response(
            main_content = 'OK',
        )


@method_decorator( edit_required, name='dispatch' )
class AddRemoveView( View, EditViewMixin ):

    def get( self, request, *args, **kwargs ):

        if request.view_parameters.view_type.is_location_view:
            return location_edit_views.LocationViewAddRemoveItemView().get( request, *args, **kwargs )

        if request.view_parameters.view_type.is_collection:
            return collection_edit_views.CollectionAddRemoveItemView().get( request, *args, **kwargs )

        context = {
        }
        return self.get_edit_side_panel_response(
            request = request,
            template_name = 'edit/panes/default.html',
            context = context,
        )

    
@method_decorator( edit_required, name='dispatch' )
class ReorderItemsView( View, EditViewMixin ):

    def post( self, request, *args, **kwargs ):
        try:
            html_id_list = json.loads( request.POST.get( 'html_id_list' ) )
        except Exception as e:
            return bad_request_response( request, message = str(e) )

        try:
            item_types = set()
            item_id_list = list()
            for html_id in html_id_list:
                ( item_type, item_id ) = self.parse_html_id( html_id )
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
        if item_type == 'entity':
            if not request.view_parameters.view_type.is_collection:
                return bad_request_response( request, message = f'Entity reordering for collections only.' )
            return collection_edit_views.CollectionReorderEntitiesView().post(
                request,
                collection_id = request.view_parameters.collection_id,
                entity_id_list = json.dumps( item_id_list ),
            )

        elif item_type == 'collection':
            return collection_edit_views.CollectionReorder().post(
                request,
                collection_id_list = json.dumps( item_id_list ),
            )

        elif item_type == 'location-view':
            return location_edit_views.LocationViewReorder().post(
                request,
                location_view_id_list = json.dumps( item_id_list ),
            )

        else:
            return bad_request_response( request, message = f'Unknown item type: {item_type}' )
