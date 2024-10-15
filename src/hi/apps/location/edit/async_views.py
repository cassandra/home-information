import json
import logging

from django.core.exceptions import BadRequest
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.location.location_manager import LocationManager

from hi.decorators import edit_required
from hi.hi_async_view import HiSideView

logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class LocationViewManageItemsView( HiSideView ):

    def get_template_name( self ) -> str:
        return 'location/edit/panes/location_view_manage_items.html'

    def get_template_context( self, request, *args, **kwargs ):

        location_view = request.view_parameters.location_view
        location_manager = LocationManager()
        entity_view_group_list = location_manager.create_entity_view_group_list(
            location_view = location_view,
        )
        collection_view_group = location_manager.create_collection_view_group(
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

    
    
