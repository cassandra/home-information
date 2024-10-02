import re
from typing import Dict

from django.http import HttpRequest
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.location.forms import SvgPositionForm
from hi.apps.location.location_view_manager import LocationViewManager
from hi.apps.location.models import Location, LocationView

from hi.constants import DIVID
from hi.enums import EditMode

from .helpers import EditHelpers


class EditViewMixin:

    def parse_html_id( self, html_id : str ):
        m = re.match( r'^hi-(\w+)-(\d+)$', html_id )
        if not m:
            raise NotImplementedError( 'Not yet handling bad edit details html id' )
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

    def render_location_view_content( self,
                                      request        : HttpRequest,
                                      location_view : LocationView ) -> str:
        location_view_data = LocationViewManager().get_location_view_data(
            location_view = location_view,
        )
        context = {
            'location_view_data': location_view_data,
        }
        template = get_template( 'location/location_view.html' )
        return template.render( context, request = request )
        
    
class EditStartView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.
        
        request.view_parameters.edit_mode = EditMode.ON
        request.view_parameters.to_session( request )

        redirect_url = request.META.get('HTTP_REFERER')
        if not redirect_url:
            redirect_url = reverse('home')
        return redirect( redirect_url )

    
class EditEndView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.

        request.view_parameters.edit_mode = EditMode.OFF
        request.view_parameters.to_session( request )

        redirect_url = request.META.get('HTTP_REFERER')
        if not redirect_url:
            redirect_url = reverse('home')
        return redirect( redirect_url )

    
class EditDetailsView( View, EditViewMixin ):

    def get(self, request, *args, **kwargs):
        if request.view_parameters.edit_mode == EditMode.OFF:
            raise NotImplementedError( 'Not yet handling bad edit context' )

        html_id = kwargs.get('html_id')
        if not html_id:
            return self.get_default_details( request )
            
        ( item_type, item_id ) = self.parse_html_id( kwargs.get('html_id'))

        if item_type == 'entity':
            return self.get_entity_details( request, entity_id = item_id )
        if item_type == 'collection':
            return self.get_collection_details( request, collection_id = item_id )
        raise NotImplementedError( 'Not yet handling unknown edit detail type.' )

    def get_default_details( self, request ):
        return self.get_edit_side_panel_response(
            request = request,
            template_name = 'edit/panes/default.html',
        )

    def get_entity_details( self, request, entity_id : int ):
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise NotImplementedError( 'Handling bad entity Id not yet implemented' )

        location_view = request.view_parameters.location_view
        entity_position = EntityPosition.objects.filter(
            entity = entity,
            location = location_view.location,
        ).first()

        svg_position_form = SvgPositionForm.from_svg_position_model( entity_position )
            
        context = {
            'entity': entity,
            'svg_position_form': svg_position_form,
        }
        return self.get_edit_side_panel_response(
            request = request,
            template_name = 'edit/panes/entity.html',
            context = context,
        )
        
    def get_collection_details( self, request, collection_id : int ):
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            raise NotImplementedError( 'Handling bad collection Id not yet implemented' )

        location_view = request.view_parameters.location_view
        collection_position = CollectionPosition.objects.filter(
            collection = collection,
            location = location_view.location,
        ).first()

        svg_position_form = SvgPositionForm.from_svg_position_model( collection_position )
            
        context = {
            'collection': collection,
            'svg_position_form': svg_position_form,
        }
        return self.get_edit_side_panel_response(
            request = request,
            template_name = 'edit/panes/collection.html',
            context = context,
        )
        
                
class EditSvgPositionView( View, EditViewMixin ):

    def post(self, request, *args, **kwargs):
        if request.view_parameters.edit_mode == EditMode.OFF:
            raise NotImplementedError( 'Not yet handling bad edit context' )
        
        ( item_type, item_id ) = self.parse_html_id( kwargs.get('html_id'))

        location_view = request.view_parameters.location_view
        if item_type == 'entity':
            svg_position_model = self.get_entity_position(
                entity_id = item_id,
                location = location_view.location,
            )
        elif item_type == 'collection':
            svg_position_model = self.get_collection_position(
                collection_id = item_id,
                location = location_view.location,
            )
        else:
            raise NotImplementedError( 'Not yet handling unknown edit detail type.' )

        svg_position_form = SvgPositionForm(
            request.POST,
            item_html_id = svg_position_model.svg_item.html_id,
        )
        if svg_position_form.is_valid():
            svg_position_form.to_svg_position_model( svg_position_model )
            svg_position_model.save()

        svg_position_item = svg_position_model.svg_item            
        context = {
            'svg_position_form': svg_position_form,
        }
        template = get_template('edit/panes/svg_position.html')
        content = template.render( context, request = request )

        insert_map = {
            svg_position_form.content_html_id: content,
        }
        set_attributes_map = {
            svg_position_item.html_id: {
                'transform': svg_position_item.transform_str,
            }
        }            
        return antinode.response(
            insert_map = insert_map,
            set_attributes_map = set_attributes_map,
        )

    def get_entity_position( self,
                             entity_id  : int,
                             location   : Location ):
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise NotImplementedError( 'Handling bad entity Id not yet implemented' )
        
        entity_position = EntityPosition.objects.filter(
            entity = entity,
            location = location,
        ).first()
        if entity_position:
            return entity_position
        return EntityPosition(
            entity = entity,
            location = location,
        )
        
    def get_collection_position( self,
                                 collection_id  : int,
                                 location   : Location ):
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            raise NotImplementedError( 'Handling bad collection Id not yet implemented' )
        
        collection_position = CollectionPosition.objects.filter(
            collection = collection,
            location = location,
        ).first()
        if collection_position:
            return collection_position
        
        return CollectionPosition(
            collection = collection,
            location = location,
        )


class EditAddRemoveView( View, EditViewMixin ):

    def get(self, request, *args, **kwargs):

        location_view = request.view_parameters.location_view

        entity_view_group_list = EditHelpers.create_entity_view_group_list( location_view = location_view )
        collection_view_group = EditHelpers.create_collection_view_group( location_view = location_view )
        
        context = {
            'entity_view_group_list': entity_view_group_list,
            'collection_view_group': collection_view_group,
        }
        return self.get_edit_side_panel_response(
            request = request,
            template_name = 'edit/panes/add_remove.html',
            context = context,
        )

    
class EditViewEntityToggleView( View, EditViewMixin ):

    def post(self, request, *args, **kwargs):

        location_view_id = kwargs.get('location_view_id')
        entity_id = kwargs.get('entity_id')

        entity = Entity.objects.get( id = entity_id )
        location_view = LocationView.objects.get( id = location_view_id )
        exists_in_view = EditHelpers.toggle_entity_in_view(
            entity = entity,
            location_view = location_view,
        )
            
        context = {
            'location_view': location_view,
            'entity': entity,
            'exists_in_view': exists_in_view,
        }
        template = get_template( 'edit/panes/edit_view_entity_toggle.html' )
        main_content = template.render( context, request = request )

        location_view_content = self.render_location_view_content(
            request = request,
            location_view = location_view,
        )
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : location_view_content,
            },
        )

    
class EditViewCollectionToggleView( View, EditViewMixin ):

    def post(self, request, *args, **kwargs):

        location_view_id = kwargs.get('location_view_id')
        collection_id = kwargs.get('collection_id')

        collection = Collection.objects.get( id = collection_id )
        location_view = LocationView.objects.get( id = location_view_id )
        exists_in_view = EditHelpers.toggle_collection_in_view(
            collection = collection,
            location_view = location_view,
        )
            
        context = {
            'location_view': location_view,
            'collection': collection,
            'exists_in_view': exists_in_view,
        }
        template = get_template( 'edit/panes/edit_view_collection_toggle.html' )
        main_content = template.render( context, request = request )

        location_view_content = self.render_location_view_content(
            request = request,
            location_view = location_view,
        )
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : location_view_content,
            },
        )
