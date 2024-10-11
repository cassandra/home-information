import logging

from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.common.utils import is_ajax
from hi.enums import ViewType
from hi.hi_grid_view import HiGridView
from hi.views import bad_request_response, page_not_found_response

from hi.constants import DIVID

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
            return bad_request_response( request, message = 'No collections defined.' )

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
            message = f'Collection "{collection_id}" does not exist.'
            logger.warning( message )
            return bad_request_response( request, message = message )

        # Remember last collection chosen
        view_type_changed = bool( request.view_parameters.view_type != ViewType.COLLECTION )
        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.collection_id = collection.id
        request.view_parameters.to_session( request )

        # When in edit mode, a collection change needs a full
        # synchronous page load to ensure any front-end editing state and
        # views are invalidated. Else, the editing state and edit side
        # panel will be invalid for the new view.
        #
        if view_type_changed and is_ajax( request ):
            sync_url = reverse( 'collection_view', kwargs = kwargs )
            return antinode.redirect_response( url = sync_url )

        collection_data = CollectionManager().get_collection_data(
            collection = collection,
        )
        context = {
            'is_async_request': is_ajax( request ),
            'collection': collection,
            'collection_data': collection_data,
        }

        side_template_name = None
        if request.is_editing:
            collection_detail_data = CollectionManager().get_collection_detail_data(
                collection = collection,
                current_location_view = None,
                is_editing = request.is_editing,
            )
            context['collection_detail_data'] = collection_detail_data
            side_template_name = 'edit/panes/side.html'

        return self.hi_grid_response( 
            request = request,
            context = context,
            main_template_name = 'collection/collection_view.html',
            side_template_name = side_template_name,
            push_url_name = 'collection_view',
            push_url_kwargs = kwargs,
        )

    
class CollectionDetailsView( View ):

    def get( self, request, *args, **kwargs ):
        collection_id = kwargs.get( 'collection_id' )
        if not collection_id:
            return bad_request_response( request, message = 'Missing collection id in request.' )
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            return page_not_found_response( request )

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = request.view_parameters.location_view

        collection_detail_data = CollectionManager().get_collection_detail_data(
            collection = collection,
            current_location_view = current_location_view,
            is_editing = request.is_editing,
        )
        
        context = {
            'collection_detail_data': collection_detail_data,
        }
        template = get_template( 'collection/panes/collection_details.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
            },
        )     

    
    
