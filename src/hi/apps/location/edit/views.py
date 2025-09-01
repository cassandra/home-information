import json
import logging

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.edit.views import CollectionPositionEditView
from hi.apps.collection.models import Collection
import hi.apps.common.antinode as antinode
from hi.apps.entity.edit.views import EntityPositionEditView
from hi.apps.entity.entity_manager import EntityManager
from hi.apps.entity.models import Entity
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import Location
from hi.apps.location.transient_models import LocationEditModeData, LocationViewEditModeData
from hi.apps.location.view_mixins import LocationViewMixin

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.enums import ItemType, ViewType
from hi.hi_async_view import HiModalView, HiSideView

from . import forms
from .view_mixins import LocationEditViewMixin

logger = logging.getLogger(__name__)


class LocationEditModeView( HiSideView, LocationViewMixin ):
    """Location edit mode panel view - shows location properties editing interface."""

    def get_template_name( self ) -> str:
        return 'location/edit/panes/location_edit_mode_panel.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        location = self.get_location( request, *args, **kwargs )
        location_edit_data = LocationEditModeData(
            location = location,
        )
        return location_edit_data.to_template_context()
    
    def post( self, request, *args, **kwargs ):
        return HttpResponseNotAllowed(['GET'])


@method_decorator( edit_required, name='dispatch' )
class LocationViewEditModeView( HiSideView, LocationViewMixin, LocationEditViewMixin ):
    """Location view edit mode panel view - shows location view properties editing interface and handles form submission."""

    def get_template_name( self ) -> str:
        return 'location/edit/panes/location_view_edit_mode_panel.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )
        location_view_edit_data = LocationViewEditModeData(
            location_view = location_view,
        )
        return location_view_edit_data.to_template_context()
    
    def post( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )
        location_view_edit_form = forms.LocationViewEditForm( request.POST, instance = location_view )
        
        if not location_view_edit_form.is_valid():
            location_view_edit_data = LocationViewEditModeData(
                location_view = location_view,
                location_view_edit_form = location_view_edit_form,
            )
            return self.location_view_edit_mode_response(
                request = request,
                location_view_edit_data = location_view_edit_data,
                status_code = 400,
            )
        
        # Location View name/order can impact many parts of UI. Full refresh is safest in this case.
        location_view_edit_form.save()     
        return antinode.refresh_response()


class LocationItemEditModeView( View ):

    def get(self, request, *args, **kwargs):
        try:
            ( item_type, item_id ) = ItemType.parse_from_dict( kwargs )
        except ValueError:
            raise BadRequest( 'Bad item id.' )
        
        if item_type == ItemType.ENTITY:
            redirect_url = reverse( 'entity_edit_mode', kwargs = { 'entity_id': item_id } )
            return HttpResponseRedirect( redirect_url )
    
        if item_type == ItemType.COLLECTION:
            redirect_url = reverse( 'collection_edit_mode', kwargs = { 'collection_id': item_id } )
            return HttpResponseRedirect( redirect_url )

        raise BadRequest( f'Unknown item type "{item_type}".' )


@method_decorator( edit_required, name='dispatch' )
class LocationAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_add.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'location_add_form': forms.LocationAddForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        
        location_add_form = forms.LocationAddForm( request.POST, request.FILES )
        if not location_add_form.is_valid():
            context = {
                'location_add_form': location_add_form,
            }
            return self.modal_response( request, context )

        try:
            location = LocationManager().create_location(
                name = location_add_form.cleaned_data.get('name'),
                svg_fragment_filename = location_add_form.cleaned_data.get('svg_fragment_filename'),
                svg_fragment_content = location_add_form.cleaned_data.get('svg_fragment_content'),
                svg_viewbox = location_add_form.cleaned_data.get('svg_viewbox'),
            )
        except ValueError as ve:
            raise BadRequest( str(ve) )

        location_view = location.views.order_by( 'order_id' ).first()
        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.update_location_view( location_view )
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )

    
class LocationAddFirstView( LocationAddView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_add_first.html'

    
@method_decorator( edit_required, name='dispatch' )
class LocationSvgReplaceView( HiModalView, LocationViewMixin ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_svg_replace.html'

    def get( self, request, *args, **kwargs ):
        location = self.get_location( request, *args, **kwargs )

        context = {
            'location': location,
            'location_svg_file_form': forms.LocationSvgReplaceForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        try:
            location_id = int( kwargs.get( 'location_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location id.' )
        try:
            location = LocationManager().get_location(
                request = request,
                location_id = location_id,
            )
        except Location.DoesNotExist:
            raise Http404( request )
        
        location_svg_file_form = forms.LocationSvgReplaceForm( request.POST, request.FILES )
        if not location_svg_file_form.is_valid():
            context = {
                'location': location,
                'location_svg_file_form': location_svg_file_form,
            }
            return self.modal_response( request, context )

        try:
            location = LocationManager().update_location_svg(
                location = location,
                svg_fragment_filename = location_svg_file_form.cleaned_data.get('svg_fragment_filename'),
                svg_fragment_content = location_svg_file_form.cleaned_data.get('svg_fragment_content'),
                svg_viewbox = location_svg_file_form.cleaned_data.get('svg_viewbox'),
            )
        except ValueError as ve:
            raise BadRequest( str(ve) )

        redirect_url = reverse('home')
        return antinode.redirect_response( redirect_url )


class LocationPropertiesEditView( View, LocationViewMixin, LocationEditViewMixin ):
    """Handle location properties editing (name, order_id, svg_view_box_str) only - used by sidebar"""

    def post( self, request, *args, **kwargs ):
        location = self.get_location( request, *args, **kwargs )

        location_edit_form = forms.LocationEditForm( request.POST, instance = location )
        form_valid = location_edit_form.is_valid()
        
        if form_valid:
            with transaction.atomic():
                location_edit_form.save()
            status_code = 200
        else:
            status_code = 400
            
        # For properties editing, we create LocationEditModeData without formset
        location_edit_data = LocationEditModeData(
            location = location,
            location_edit_form = location_edit_form,
        )
        return self.location_properties_response(
            request = request,
            location_edit_data = location_edit_data,
            status_code = status_code,
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationDeleteView( HiModalView, LocationViewMixin ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_delete.html'

    def get(self, request, *args, **kwargs):
        location = self.get_location( request, *args, **kwargs )

        context = {
            'location': location,
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        try:
            location_id = int( kwargs.get('location_id'))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid location id.' )
        try:
            location = LocationManager().get_location(
                request = request,
                location_id = location_id,
            )
        except Location.DoesNotExist:
            raise Http404( request )

        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        location.delete()

        if request.view_parameters.location_id == location_id:
            request.view_parameters.update_location_view( location_view = None )
            request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

        
@method_decorator( edit_required, name='dispatch' )
class LocationViewAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_view_add.html'
    
    def get( self, request, *args, **kwargs ):
        try:
            # Ensure we have a location to add the view to.
            location = LocationManager().get_default_location( request = request )
        except Location.DoesNotExist:
            raise BadRequest( 'No locations defined.' )
        context = {
            'location': location,
            'location_view_add_form': forms.LocationViewAddForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        try:
            current_location = LocationManager().get_default_location( request = request )
        except Location.DoesNotExist:
            raise BadRequest( 'No locations defined.' )

        location_view_add_form = forms.LocationViewAddForm( request.POST )
        if not location_view_add_form.is_valid():
            context = {
                'location_view_add_form': location_view_add_form,
            }
            return self.modal_response( request, context )

        try:
            location_view = LocationManager().create_location_view(
                location = current_location,
                name = location_view_add_form.cleaned_data.get('name'),
            )
        except ValueError as e:
            raise BadRequest( str(e) )

        request.view_parameters.view_type = ViewType.LOCATION_VIEW
        request.view_parameters.update_location_view( location_view = location_view )
        request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewDeleteView( HiModalView, LocationViewMixin ):

    def get_template_name( self ) -> str:
        return 'location/edit/modals/location_view_delete.html'
    
    def get(self, request, *args, **kwargs):
        location_view = self.get_location_view( request, *args, **kwargs )

        context = {
            'location_view': location_view,
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )

        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        location_view.delete()

        if request.view_parameters.location_view_id == location_view.id:
            request.view_parameters.update_location_view( location_view = None )
            request.view_parameters.to_session( request )
        
        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

    

    
class LocationViewGeometryView( View, LocationViewMixin, LocationEditViewMixin ):

    def post(self, request, *args, **kwargs):
        location_view = self.get_location_view( request, *args, **kwargs )

        location_view_geometry_form = forms.LocationViewGeometryForm( request.POST, instance = location_view )
        if location_view_geometry_form.is_valid():
            location_view_geometry_form.save()
            status_code = 200
        else:
            # LocationViewGeometryForm is just a subset of
            # LocationViewEditForm used when Javascript mouse/key editing
            # causes a change to the geometry.  This could give some visual
            # indicator to the user, but if this chag7e was successfully
            # applied in the DOM, then the only issue would be some
            # internal or API issue.
            logger.warning( 'LocationView geometry form is invalid.' )
            status_code = 400

        location_view_edit_data = LocationViewEditModeData(
            location_view = location_view,
        )       
        return self.location_view_edit_mode_response(
            request = request,
            location_view_edit_data = location_view_edit_data,
            status_code = status_code,
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewManageItemsView( HiSideView ):

    def get_template_name( self ) -> str:
        return 'location/edit/panes/location_view_manage_items.html'

    def get_template_context( self, request, *args, **kwargs ):
        
        location_view = LocationManager().get_default_location_view( request = request )
        entity_view_group_list = EntityManager().create_location_entity_view_group_list(
            location_view = location_view,
        )
        collection_view_group = CollectionManager().create_location_collection_view_group(
            location_view = location_view,
        )
        return {
            'location_view': location_view,
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
class LocationViewEntityToggleView( View, LocationViewMixin ):

    def post( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )

        try:
            entity_id = int( kwargs.get('entity_id'))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid entity id.' )
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404( request )

        exists_in_view = EntityManager().toggle_entity_in_view(
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
            include_status_display_data = bool( not request.view_parameters.is_editing ),
        )
        context = {
            'location_view': location_view,
            'location_view_data': location_view_data,
        }
        template = get_template( self.LOCATION_VIEW_TEMPLATE_NAME )
        location_view_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : location_view_content,
            },
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewCollectionToggleView( View, LocationViewMixin ):

    def post(self, request, *args, **kwargs):
        location_view = self.get_location_view( request, *args, **kwargs )

        try:
            collection_id = int( kwargs.get('collection_id'))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid collection id.' )
        try:
            collection = CollectionManager().get_collection(
                request = request,
                collection_id = collection_id,
            )
        except Collection.DoesNotExist:
            raise Http404( request )

        exists_in_view = CollectionManager().toggle_collection_in_view(
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
            include_status_display_data = bool( not request.view_parameters.is_editing ),
        )
        context = {
            'location_view': location_view,
            'location_view_data': location_view_data,
        }
        template = get_template( self.LOCATION_VIEW_TEMPLATE_NAME )
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
        
        location = LocationManager().get_default_location( request = request )
        if item_type == ItemType.ENTITY:
            EntityManager().set_entity_path(
                entity_id = item_id,
                location = location,
                svg_path_str = svg_path_str,
            )
        elif item_type == ItemType.COLLECTION:
            collection = CollectionManager().get_collection(
                request = request,
                collection_id = item_id,
            )
            CollectionManager().set_collection_path(
                collection = collection,
                location = location,
                svg_path_str = svg_path_str,
            )
        else:
            raise BadRequest( f'Cannot set SVG path for "{item_type}"' )

        return antinode.response(
            main_content = 'OK',
        )
