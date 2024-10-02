import logging

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax
from hi.enums import ViewType
from hi.hi_grid_view import HiGridView

from .collection_manager import CollectionManager
from .models import Collection

logger = logging.getLogger(__name__)


class CollectionViewDefaultView( View ):

    def get(self, request, *args, **kwargs):

        collection = self._get_default_collection( request )
        redirect_url = reverse(
            'collection_view',
            kwargs = { 'id': collection.id }
        )
        return HttpResponseRedirect( redirect_url )

    def _get_default_collection( self, request ):
        if request.view_parameters.collection:
            return request.view_parameters.collection

        collection = Collection.objects.order_by( 'order_id' ).first()
        if not collection:
            raise NotImplementedError('Handling no defined collections not yet implemented')

        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.collection_id = collection.id
        request.view_parameters.to_session( request )
        return collection
    
    
class CollectionView( HiGridView ):

    def get(self, request, *args, **kwargs):

        collection_id = kwargs.get('id')
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            logger.warning( f'Collection "{collection_id}" does not exist.' )
            raise NotImplementedError('Handling bad collection not yet implemented')

        # Remember last collection chosen
        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.collection_id = collection.id
        request.view_parameters.to_session( request )

        # When in edit mode, a collection change needs a full
        # synchronous page load to ensure any front-end editing state and
        # views are invalidated. Else, the editing state and edit side
        # panel will be invalid for the new view.
        #
        if is_ajax( request ) and request.view_parameters.view_mode.should_reload_on_view_change:
            sync_url = reverse( 'collection_view', kwargs = kwargs )
            return antinode.redirect_response( url = sync_url )

        collection_data = CollectionManager().get_collection_data(
            collection = collection,
        )
        context = {
            'is_async_request': is_ajax( request ),
            'collection_data': collection_data,
        }
        return self.hi_grid_response( 
            request = request,
            context = context,
            main_template_name = 'collection/collection_view.html',
            push_url_name = 'collection_view',
            push_url_kwargs = kwargs,
        )
