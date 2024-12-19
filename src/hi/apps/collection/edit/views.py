import json
import logging

from django.core.exceptions import BadRequest
from django.db import transaction
from django.http import Http404
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionPosition
from hi.apps.collection.transient_models import CollectionEditData
from hi.apps.collection.view_mixin import CollectionViewMixin
import hi.apps.common.antinode as antinode
from hi.apps.entity.view_mixin import EntityViewMixin
from hi.apps.location.location_manager import LocationManager
from hi.apps.location.models import LocationView
from hi.apps.location.svg_item_factory import SvgItemFactory

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.enums import ViewType
from hi.hi_async_view import HiModalView, HiSideView

from . import forms

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class CollectionAddView( HiModalView ):

    def get_template_name( self ) -> str:
        return 'collection/edit/modals/collection_add.html'

    def get( self, request, *args, **kwargs ):
        context = {
            'collection_form': forms.CollectionForm(),
        }
        return self.modal_response( request, context )
    
    def post( self, request, *args, **kwargs ):
        collection_form = forms.CollectionForm( request.POST )
        if not collection_form.is_valid():
            context = {
                'collection_form': collection_form,
            }
            return self.modal_response( request, context )

        with transaction.atomic():
            collection = collection_form.save()
            if request.view_parameters.view_type == ViewType.LOCATION_VIEW:
                self._add_to_location_view(
                    request = request,
                    collection = collection,
                )

        if request.view_parameters.view_type == ViewType.COLLECTION:
            request.view_parameters.update_collection( collection = collection )
            request.view_parameters.to_session( request )

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )

    def _add_to_location_view( self, request, collection : Collection ):
        try:
            # Ensure we have a location view to add the entity to.
            current_location_view = LocationManager().get_default_location_view( request = request )
            CollectionManager().create_collection_view(
                collection = collection,
                location_view = current_location_view,
            )
        except LocationView.DoesNotExist:
            logger.warning( 'No current location view to add new collection to.')

        return

    
@method_decorator( edit_required, name='dispatch' )
class CollectionDeleteView( HiModalView, CollectionViewMixin ):

    def get_template_name( self ) -> str:
        return 'collection/edit/modals/collection_delete.html'

    def get(self, request, *args, **kwargs):
        collection = self.get_collection( request, *args, **kwargs )

        context = {
            'collection': collection,
        }
        return self.modal_response( request, context )

    def post( self, request, *args, **kwargs ):
        collection = self.get_collection( request, *args, **kwargs )

        action = request.POST.get( 'action' )
        if action != 'confirm':
            raise BadRequest( 'Missing confirmation value.' )

        collection.delete()

        if request.view_parameters.collection_id == collection.id:
            request.view_parameters.update_collection( collection = None )
            request.view_parameters.to_session( request )

        redirect_url = reverse('home')
        return self.redirect_response( request, redirect_url )
    

class CollectionEditView( View, CollectionViewMixin ):
    
    def post( self, request, *args, **kwargs ):
        collection = self.get_collection( request, *args, **kwargs )

        collection_form = forms.CollectionForm( request.POST, instance = collection )
        if collection_form.is_valid():
            collection_form.save()
            # Change can impact other parts of UI. e.g., Collection name shows on bottom of screen
            return antinode.refresh_response()

        # On error, show form errors        
        collection_edit_data = CollectionEditData(
            collection = collection,
            collection_form = collection_form,
        )
        return self.collection_edit_response(
            request = request,
            collection_edit_data = collection_edit_data,
            status_code = 400,
        )

        
@method_decorator( edit_required, name='dispatch' )
class CollectionReorder( View ):
    
    def post(self, request, *args, **kwargs):
        try:
            collection_id_list = json.loads( kwargs.get( 'collection_id_list' ) )
        except Exception as e:
            raise BadRequest( str(e) )

        if not collection_id_list:
            raise BadRequest( 'Missing collection ids.' )

        CollectionManager().set_collection_order(
            collection_id_list = collection_id_list,
        )
        return antinode.response( main_content = 'OK' )
    
    
@method_decorator( edit_required, name='dispatch' )
class CollectionPositionEditView( View, CollectionViewMixin ):

    def post(self, request, *args, **kwargs):
        collection = self.get_collection( request, *args, **kwargs )

        location = LocationManager().get_default_location( request = request )
        try:
            collection_position = CollectionPosition.objects.get(
                collection = collection,
                location = location,
            )
        except CollectionPosition.DoesNotExist:
            logger.warning( f'Not collection position found for {collection} at {location}' )
            raise Http404( request )

        collection_position_form = forms.CollectionPositionForm(
            request.POST,
            instance = collection_position,
        )
        if collection_position_form.is_valid():
            collection_position_form.save()
        else:
            logger.warning( 'CollectionPosition form is invalid.' )
            
        context = {
            'collection': collection_position.collection,
            'collection_position_form': collection_position_form,
        }
        template = get_template( 'collection/edit/panes/collection_position_edit.html' )
        content = template.render( context, request = request )
        insert_map = {
            DIVID['COLLECTION_POSITION_EDIT_PANE']: content,
        }

        svg_icon_item = SvgItemFactory().create_svg_icon_item(
            item = collection_position.collection,
            position = collection_position,
            css_class = '',
        )
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
class CollectionManageItemsView( HiSideView ):

    def get_template_name( self ) -> str:
        return 'collection/edit/panes/collection_manage_items.html'

    def get_template_context( self, request, *args, **kwargs ):

        collection = CollectionManager().get_default_collection( request = request )
        entity_collection_group_list = CollectionManager().create_entity_collection_group_list(
            collection = collection,
        )
        return {
            'entity_collection_group_list': entity_collection_group_list,
        }

    
@method_decorator( edit_required, name='dispatch' )
class CollectionReorderEntitiesView( View, CollectionViewMixin ):
    
    def post(self, request, *args, **kwargs):
        collection = self.get_collection( request, *args, **kwargs )
            
        try:
            entity_id_list = json.loads( kwargs.get( 'entity_id_list' ) )
        except Exception as e:
            raise BadRequest( str(e) )

        if not entity_id_list:
            raise BadRequest( 'Missing entity ids.' )

        CollectionManager().set_collection_entity_order(
            collection = collection,
            entity_id_list = entity_id_list,
        )
        return antinode.response( main_content = 'OK' )

        
@method_decorator( edit_required, name='dispatch' )
class CollectionEntityToggleView( View, CollectionViewMixin, EntityViewMixin ):

    def post(self, request, *args, **kwargs):
        collection = self.get_collection( request, *args, **kwargs )
        entity = self.get_entity( request, *args, **kwargs )

        exists_in_collection = CollectionManager().toggle_entity_in_collection(
            entity = entity,
            collection = collection,
        )
            
        context = {
            'collection': collection,
            'entity': entity,
            'exists_in_collection': exists_in_collection,
        }
        template = get_template( 'collection/edit/panes/collection_entity_toggle.html' )
        main_content = template.render( context, request = request )

        collection_data = CollectionManager().get_collection_data(
            collection = collection,
            is_editing = request.view_parameters.is_editing,
        )
        context = collection_data.to_template_context()
        template = get_template( 'collection/panes/collection_view.html' )
        collection_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : collection_content,
            },
        )
    
