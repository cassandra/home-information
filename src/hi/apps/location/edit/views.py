from decimal import Decimal
import json
import logging

from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
import hi.apps.collection.views as collection_views
from hi.apps.collection.models import Collection
import hi.apps.common.antinode as antinode
from hi.apps.common.svg_models import SvgViewBox
from hi.apps.entity.entity_manager import EntityManager
import hi.apps.entity.views as entity_views
from hi.apps.entity.models import Entity
from hi.apps.location.forms import LocationItemPositionForm
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location, LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory
import hi.apps.location.views as location_views
from hi.decorators import edit_required
from hi.enums import ItemType, ViewType
from hi.hi_grid_view import HiGridView
from hi.views import (
    bad_request_response,
    internal_error_response,
    page_not_found_response,
)

from hi.constants import DIVID

from . import forms


logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class LocationAddView( View ):

    def get( self, request, *args, **kwargs ):
        return self._show_modal( request, location_form = forms.LocationForm() )
    
    def post( self, request, *args, **kwargs ):
        location_form = forms.LocationForm( request.POST, request.FILES )
        if not location_form.is_valid():
            return self._show_modal( request, location_form = location_form )

        try:
            location = LocationManager().create_location(
                name = location_form.cleaned_data.get('name'),
                svg_fragment_filename = location_form.cleaned_data.get('svg_fragment_filename'),
                svg_fragment_content = location_form.cleaned_data.get('svg_fragment_content'),
                svg_viewbox = location_form.cleaned_data.get('svg_viewbox'),
            )
        except ValueError as ve:
            return bad_request_response( request, message = str(ve) )
        except Exception as e:
            logger.exception( e )
            return internal_error_response( request, message = str(e) )

        location_view = location.views.order_by( 'order_id' ).first()
        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    def _show_modal( self, request, location_form : forms.LocationForm ):
        context = {
            'location_form': location_form,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_add.html',
            context = context,
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationDeleteView( View ):

    def get(self, request, *args, **kwargs):
        location_id = kwargs.get( 'location_id' )
        if not location_id:
            return bad_request_response( request, message = 'Missing location id.' )
            
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            return page_not_found_response( request )

        context = {
            'location': location,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_delete.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            return bad_request_response( request, message = 'Missing confirmation value.' )

        location_id = kwargs.get( 'location_id' )
        if not location_id:
            return bad_request_response( request, message = 'Missing location id.' )
            
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            return page_not_found_response( request )

        location.delete()

        next_location = Location.objects.all().order_by( 'order_id' ).first()
        if next_location:
            request.view_parameters.location_id = next_location.id
        else:
            request.view_parameters.location_id = None
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

        
@method_decorator( edit_required, name='dispatch' )
class LocationViewAddView( View ):

    def get( self, request, *args, **kwargs ):
        context = {
            'location_view_form': forms.LocationViewForm(),
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_view_add.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        location_view_form = forms.LocationViewForm( request.POST )
        if not location_view_form.is_valid():
            context = {
                'location_view_form': location_view_form,
            }
            return antinode.modal_from_template(
                request = request,
                template_name = 'location/edit/modals/location_view_add.html',
                context = context,
            )

        if request.view_parameters.location_view:
            location = request.view_parameters.location_view.location
        else:
            location = Location.objects.order_by( 'order_id' ).first()
        
        try:
            location_view = LocationManager().create_location_view(
                location = location,
                name = location_view_form.cleaned_data.get('name'),
            )
        except ValueError as e:
            return bad_request_response( request, message = str(e) )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    
class LocationViewGeometryView( View ):

    def post(self, request, *args, **kwargs):

        location_view_id = kwargs.get('location_view_id')
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            return page_not_found_response( request )

        try:
            svg_view_box_str = request.POST.get('view_box')
            svg_view_box = SvgViewBox.from_attribute_value( svg_view_box_str )
        except (TypeError, ValueError ):
            return bad_request_response( request, message = f'Bad viewbox: {svg_view_box_str}' )

        try:
            svg_rotate_angle = float( request.POST.get('rotate_angle'))
        except (TypeError, ValueError ):
            return bad_request_response( request, message = f'Bad rotate angle: {svg_rotate_angle}' )

        location_view.svg_view_box_str = str(svg_view_box)
        location_view.svg_rotate = Decimal( svg_rotate_angle )
        location_view.save()

        return antinode.response( main_content = 'OK' )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewReorder( View ):
    
    def post(self, request, *args, **kwargs):
        try:
            location_view_id_list = json.loads( kwargs.get( 'location_view_id_list' ) )
        except Exception as e:
            return bad_request_response( request, message = str(e) )

        if not location_view_id_list:
            return bad_request_response( request, message = 'Missing location view ids.' )

        LocationManager().set_location_view_order(
            location_view_id_list = location_view_id_list,
        )            
        return antinode.response( main_content = 'OK' )        

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewDeleteView( View ):

    def get(self, request, *args, **kwargs):
        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            return bad_request_response( request, message = 'Missing location view id.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            return page_not_found_response( request )

        context = {
            'location_view': location_view,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_view_delete.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        action = request.POST.get( 'action' )
        if action != 'confirm':
            return bad_request_response( request, message = 'Missing confirmation value.' )

        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            return bad_request_response( request, message = 'Missing location view id.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            return page_not_found_response( request )

        location_view.delete()

        next_location_view = LocationView.objects.all().order_by( 'order_id' ).first()
        if next_location_view:
            request.view_parameters.location_view_id = next_location_view.id
        else:
            request.view_parameters.location_view_id = None
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewAddRemoveItemView( View ):

    def get(self, request, *args, **kwargs):

        location_view = request.view_parameters.location_view

        location_manager = LocationManager()
        entity_view_group_list = location_manager.create_entity_view_group_list(
            location_view = location_view,
        )
        collection_view_group = location_manager.create_collection_view_group(
            location_view = location_view,
        )
        
        context = {
            'entity_view_group_list': entity_view_group_list,
            'collection_view_group': collection_view_group,
        }
        template = get_template( 'location/edit/panes/location_view_add_remove_item.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
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
class LocationItemDetailsView( HiGridView ):

    def get(self, request, *args, **kwargs):

        if not kwargs.get( ItemType.HTML_ID_ARG() ):
            return self.get_default_details( request )

        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            return bad_request_response( request, message = 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            return entity_views.EntityDetailsView().get(
                request = request,
                entity_id = item_id,
            )            

        if item_type == ItemType.COLLECTION:
            return collection_views.CollectionDetailsView().get(
                request = request,
                collection_id = item_id,
            )            

        return bad_request_response( request, message = 'Unknown item type "{item_type}".' )

    def get_default_details( self, request ):
        if request.view_parameters.view_type.is_collection:
            return collection_views.CollectionDetailsView().get(
                request = request,
                location_view_id = request.view_parameters.collection_id,
            )
        if not request.view_parameters.location_view:
            raise ValueError( 'No current location view was set.' )
        location_id = request.view_parameters.location_view.location.id
        return location_views.LocationDetailsView().get(
            request = request,
            location_id = location_id,
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationItemPositionView( View ):

    def post(self, request, *args, **kwargs):
        
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            return bad_request_response( request, messahe = 'Bad item id.' )
        
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
            return bad_request_response( request, message = f'Cannot set SVG position for "{item_type}"' )

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


