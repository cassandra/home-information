import json
import logging

from django.core.exceptions import BadRequest
from django.http import Http404
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection, CollectionPosition
import hi.apps.common.antinode as antinode
from hi.apps.entity.models import Entity
from hi.apps.location.svg_item_factory import SvgItemFactory

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.hi_async_view import HiSideView

from . import forms

logger = logging.getLogger(__name__)


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
class CollectionPositionEditView( View ):

    def post(self, request, *args, **kwargs):

        collection_id = kwargs.get('collection_id')
        location = request.view_parameters.location
        try:
            collection_position = CollectionPosition.objects.get(
                id = collection_id,
                location = location,
            )
        except Collection.DoesNotExist:
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

        collection = request.view_parameters.collection
        entity_collection_group_list = CollectionManager().create_entity_collection_group_list(
            collection = collection,
        )
        return {
            'entity_collection_group_list': entity_collection_group_list,
        }

    
@method_decorator( edit_required, name='dispatch' )
class CollectionReorderEntitiesView( View ):
    
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        if not collection_id:
            raise BadRequest( 'Missing collection id.' )
            
        try:
            entity_id_list = json.loads( kwargs.get( 'entity_id_list' ) )
        except Exception as e:
            raise BadRequest( str(e) )

        if not entity_id_list:
            raise BadRequest( 'Missing entity ids.' )

        CollectionManager().set_collection_entity_order(
            collection_id = collection_id,
            entity_id_list = entity_id_list,
        )
        return antinode.response( main_content = 'OK' )

        
@method_decorator( edit_required, name='dispatch' )
class CollectionEntityToggleView( View ):

    def post(self, request, *args, **kwargs):

        collection_id = kwargs.get('collection_id')
        entity_id = kwargs.get('entity_id')

        entity = Entity.objects.get( id = entity_id )
        collection = Collection.objects.get( id = collection_id )
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
        )
        context = {
            'collection_data': collection_data,
        }
        template = get_template( 'collection/collection_view.html' )
        collection_content = template.render( context, request = request )
        
        return antinode.response(
            main_content = main_content,
            insert_map = {
                DIVID['MAIN'] : collection_content,
            },
        )
