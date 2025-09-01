from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest
from django.template.loader import get_template

import hi.apps.common.antinode as antinode
from hi.apps.collection.collection_manager import CollectionManager
from hi.apps.collection.models import Collection
from hi.apps.collection.transient_models import CollectionEditModeData

from hi.constants import DIVID


class CollectionViewMixin:

    def get_collection( self, request, *args, **kwargs ) -> Collection:
        """ Assumes there is a required collection_id in kwargs """
        try:
            collection_id = int( kwargs.get( 'collection_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid collection id.' )
        try:
            return CollectionManager().get_collection(
                request = request,
                collection_id = collection_id,
            )
        except Collection.DoesNotExist:
            raise Http404( request )
 
    def collection_edit_mode_response( self,
                                       request               : HttpRequest,
                                       collection_edit_data  : CollectionEditModeData,
                                       status_code           : int                    = 200 ):

        context = collection_edit_data.to_template_context()
        template = get_template( 'collection/edit/panes/collection_properties_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['COLLECTION_EDIT_PANE']: content,
            },
            status = status_code,
        )
