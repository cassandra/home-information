import json
import logging

from django.core.exceptions import BadRequest
from django.utils.decorators import method_decorator
from django.views.generic import View

from hi.apps.collection.collection_manager import CollectionManager
import hi.apps.common.antinode as antinode

from hi.decorators import edit_required
from hi.hi_async_view import HiSideView

logger = logging.getLogger(__name__)


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
    
