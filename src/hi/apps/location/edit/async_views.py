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
from hi.apps.location.models import LocationAttribute
from hi.apps.location.transient_models import LocationEditData, LocationViewEditData
from hi.apps.location.view_mixin import LocationViewMixin

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.enums import ItemType
from hi.hi_async_view import HiSideView

from . import forms

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class LocationEditView( View, LocationViewMixin ):

    def post( self, request, *args, **kwargs ):
        location = self.get_location( request, *args, **kwargs )

        location_edit_form = forms.LocationEditForm(
            request.POST,
            instance = location,
        )
        location_attribute_formset = forms.LocationAttributeFormSet(
            request.POST,
            request.FILES,
            instance = location,
            prefix = f'location-{location.id}',
            form_kwargs = {
                'show_as_editable': True,
            },
        )
        
        if ( location_edit_form.is_valid()
             and location_attribute_formset.is_valid() ):
            with transaction.atomic():
                location_edit_form.save()
                location_attribute_formset.save()

            # Location name/order can impact many parts of UI. Full refresh is safest in this case.
            if location_edit_form.has_changed():
                return antinode.refresh_response()
                
            # Recreate to preserve "max" to show new form
            location_attribute_formset = forms.LocationAttributeFormSet(
                instance = location,
                prefix = f'location-{location.id}',
            )
            status_code = 200
        else:
            status_code = 400

        location_edit_data = LocationEditData(
            location = location,
            location_edit_form = location_edit_form,
            location_attribute_formset = location_attribute_formset,
        )
        return self.location_edit_response(
            request = request,
            location_edit_data = location_edit_data,
            status_code = status_code,
        )
            
    
class LocationAttributeUploadView( View, LocationViewMixin ):

    def post( self, request, *args, **kwargs ):
        location = self.get_location( request, *args, **kwargs )
        location_attribute = LocationAttribute( location = location )
        location_attribute_upload_form = forms.LocationAttributeUploadForm(
            request.POST,
            request.FILES,
            instance = location_attribute,
        )

        if location_attribute_upload_form.is_valid():
            with transaction.atomic():
                location_attribute_upload_form.save()   
            status_code = 200
        else:
            status_code = 400

        location_edit_data = LocationEditData(
            location = location,
            location_attribute_upload_form = location_attribute_upload_form,
        )
        return self.location_edit_response(
            request = request,
            location_edit_data = location_edit_data,
            status_code = status_code,
        )

    
@method_decorator( edit_required, name='dispatch' )
class LocationViewEditView( View, LocationViewMixin ):

    def post( self, request, *args, **kwargs ):
        location_view = self.get_location_view( request, *args, **kwargs )
        location_view_edit_form = forms.LocationViewEditForm( request.POST, instance = location_view )

        if not location_view_edit_form.is_valid():
            location_view_edit_data = LocationViewEditData(
                location_view = location_view,
                location_view_edit_form = location_view_edit_form,
            )
            return self.location_view_edit_response(
                request = request,
                location_view_edit_data = location_view_edit_data,
                status_code = 400,
            )
        
        # Location View name/order can impact many parts of UI. Full refresh is safest in this case.
        location_view_edit_form.save()     
        return antinode.refresh_response()

    
class LocationViewGeometryView( View, LocationViewMixin ):

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

        location_view_edit_data = LocationViewEditData(
            location_view = location_view,
        )       
        return self.location_view_edit_response(
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
        entity_view_group_list = EntityManager().create_entity_view_group_list(
            location_view = location_view,
        )
        collection_view_group = CollectionManager().create_collection_view_group(
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
            include_status_display_data = bool( not request.is_editing ),
        )
        context = {
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
            include_status_display_data = bool( not request.is_editing ),
        )
        context = {
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


    
    
