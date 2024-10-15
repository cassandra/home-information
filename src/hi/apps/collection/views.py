import logging

from django.core.exceptions import BadRequest
from django.http import HttpResponseRedirect, Http404
from django.urls import reverse
from django.views.generic import View

from hi.apps.common.utils import is_ajax
from hi.enums import ViewType
from hi.exceptions import ForceRedirectException
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
            raise BadRequest( 'No collections defined.' )

        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.collection_id = collection.id
        request.view_parameters.to_session( request )
        return collection
    
    
class CollectionView( HiGridView ):

    def get_main_template_name( self ) -> str:
        return 'collection/collection_view.html'

    def get_template_context( self, request, *args, **kwargs ):

        collection_id = kwargs.get('id')
        try:
            collection = Collection.objects.get( id = collection_id )
        except Collection.DoesNotExist:
            raise Http404()

        # Remember last collection chosen
        view_type_changed = bool( request.view_parameters.view_type != ViewType.COLLECTION )
        view_id_changed = bool( request.view_parameters.collection_id != collection.id )

        request.view_parameters.view_type = ViewType.COLLECTION
        request.view_parameters.collection_id = collection.id
        request.view_parameters.to_session( request )

        # When in edit mode, a collection change needs a full
        # synchronous page load to ensure any front-end editing state and
        # views are invalidated. Else, the editing state and edit side
        # panel will be invalid for the new view.
        #
        if ( request.is_editing
             and is_ajax( request )
             and ( view_type_changed or view_id_changed )):
            redirect_url = reverse( 'collection_view', kwargs = kwargs )
            raise ForceRedirectException( url = redirect_url )

        collection_data = CollectionManager().get_collection_data(
            collection = collection,
        )
        return {
            'is_async_request': is_ajax( request ),
            'collection': collection,
            'collection_data': collection_data,
        }


    
    
