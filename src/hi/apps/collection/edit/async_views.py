import logging

from django.utils.decorators import method_decorator

from hi.apps.collection.collection_manager import CollectionManager
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
