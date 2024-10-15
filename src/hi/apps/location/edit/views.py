from decimal import Decimal
import logging

from django.core.exceptions import BadRequest
from django.http import Http404
from django.template.loader import get_template
from django.urls import reverse
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
from hi.apps.location.models import Location, LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory
from hi.decorators import edit_required
from hi.enums import ItemType, ViewType

from hi.constants import DIVID

from . import forms


logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class LocationAddView( View ):

    def get( self, request, *args, **kwargs ):
        return self._show_modal( request, location_add_form = forms.LocationAddForm() )
    
    def post( self, request, *args, **kwargs ):
        
        location_add_form = forms.LocationAddForm( request.POST, request.FILES )
        if not location_add_form.is_valid():
            return self._show_modal( request, location_add_form = location_add_form )

        try:
            location = LocationManager().create_location(
                name = location_add_form.cleaned_data.get('name'),
                svg_fragment_filename = location_add_form.cleaned_data.get('svg_fragment_filename'),
                svg_fragment_content = location_add_form.cleaned_data.get('svg_fragment_content'),
                svg_viewbox = location_add_form.cleaned_data.get('svg_viewbox'),
            )
        except ValueError as ve:
            raise BadRequest( str(ve) )
        except Exception as e:
            logger.exception( e )
            return internal_error_response( request, message = str(e) )

        location_view = location.views.order_by( 'order_id' ).first()
        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    def _show_modal( self, request, location_add_form : forms.LocationAddForm ):
        context = {
            'location_add_form': location_add_form,
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_add.html',
            context = context,
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationEditView( View ):

    def post( self, request, *args, **kwargs ):
        raise NotImplementedError()

    
@method_decorator( edit_required, name='dispatch' )
class LocationDeleteView( View ):

    def get(self, request, *args, **kwargs):
        location_id = kwargs.get( 'location_id' )
        if not location_id:
            raise BadRequest( 'Missing location id.' )
            
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            raise Http404( request )

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
            raise BadRequest( 'Missing confirmation value.' )

        location_id = kwargs.get( 'location_id' )
        if not location_id:
            raise BadRequest( 'Missing location id.' )
            
        try:
            location = Location.objects.get( id = location_id )
        except Location.DoesNotExist:
            raise Http404( request )

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
            'location_view_add_form': forms.LocationViewAddForm(),
        }
        return antinode.modal_from_template(
            request = request,
            template_name = 'location/edit/modals/location_view_add.html',
            context = context,
        )
    
    def post( self, request, *args, **kwargs ):
        location_view_add_form = forms.LocationViewAddForm( request.POST )
        if not location_view_add_form.is_valid():
            context = {
                'location_view_add_form': location_view_add_form,
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
                name = location_view_add_form.cleaned_data.get('name'),
            )
        except ValueError as e:
            raise BadRequest( str(e) )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.location_view_id = location_view.id
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    
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
class LocationViewDeleteView( View ):

    def get(self, request, *args, **kwargs):
        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            raise BadRequest( 'Missing location view id.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            raise Http404( request )

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
            raise BadRequest( 'Missing confirmation value.' )

        location_view_id = kwargs.get( 'location_view_id' )
        if not location_view_id:
            raise BadRequest( 'Missing location view id.' )
            
        try:
            location_view = LocationView.objects.select_related(
                'location' ).get( id = location_view_id )
        except LocationView.DoesNotExist:
            raise Http404( request )

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


