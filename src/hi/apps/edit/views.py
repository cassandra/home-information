import json
import logging

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.collection.edit.views as collection_edit_views
import hi.apps.location.edit.views as location_edit_views
from hi.decorators import edit_required
from hi.enums import ItemType
from hi.views import bad_request_response

from hi.enums import ViewMode

logger = logging.getLogger(__name__)


class EditStartView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.
        
        request.view_parameters.view_mode = ViewMode.EDIT
        request.view_parameters.to_session( request )

        redirect_url = request.META.get('HTTP_REFERER')
        if not redirect_url:
            redirect_url = reverse('home')
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class EditEndView( View ):

    def get(self, request, *args, **kwargs):

        # This most do a full synchronous page load to ensure that the
        # Javascript handling is consistent with the current operating
        # state mode.

        request.view_parameters.view_mode = ViewMode.MONITOR
        request.view_parameters.to_session( request )

        redirect_url = request.META.get('HTTP_REFERER')
        if not redirect_url:
            redirect_url = reverse('home')
        return redirect( redirect_url )

    
@method_decorator( edit_required, name='dispatch' )
class ReorderItemsView( View ):

    def post( self, request, *args, **kwargs ):
        try:
            item_type_id_list = ItemType.parse_list_from_dict( request.POST )
        except ValueError as e:
            return bad_request_response( request, message = str(e) )

        try:
            item_types = set()
            item_id_list = list()
            for item_type, item_id in item_type_id_list:
                item_types.add( item_type )
                item_id_list.append( item_id )
                continue
        except ValueError as ve:
            return bad_request_response( request, message = str(ve) )
            
        if len(item_types) < 1:
            return bad_request_response( request, message = 'No ids found' )

        if len(item_types) > 1:
            return bad_request_response( request, message = f'Too many item types: {item_types}' )

        item_type = next(iter(item_types))
        if item_type == ItemType.ENTITY:
            if not request.view_parameters.view_type.is_collection:
                return bad_request_response( request, message = 'Entity reordering for collections only.' )
            return collection_edit_views.CollectionReorderEntitiesView().post(
                request,
                collection_id = request.view_parameters.collection_id,
                entity_id_list = json.dumps( item_id_list ),
            )

        elif item_type == ItemType.COLLECTION:
            return collection_edit_views.CollectionReorder().post(
                request,
                collection_id_list = json.dumps( item_id_list ),
            )

        elif item_type == ItemType.LOCATION_VIEW:
            return location_edit_views.LocationViewReorder().post(
                request,
                location_view_id_list = json.dumps( item_id_list ),
            )

        else:
            return bad_request_response( request, message = f'Unknown item type: {item_type}' )
