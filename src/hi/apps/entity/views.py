import logging

from django.template.loader import get_template
from django.views.generic import View

import hi.apps.common.antinode as antinode

from hi.constants import DIVID
from hi.views import bad_request_response, page_not_found_response

from .entity_manager import EntityManager
from .models import Entity

logger = logging.getLogger(__name__)


class EntityDetailsView( View ):

    def get( self, request, *args, **kwargs ):
        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            return bad_request_response( request, message = 'Missing entity id in request.' )
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            return page_not_found_response( request, message = f'No entity with id "{entity_id}".' )

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = request.view_parameters.location_view

        entity_detail_data = EntityManager().get_entity_detail_data(
            entity = entity,
            current_location_view = current_location_view,
            is_editing = request.is_editing,
        )
        
        context = {
            'entity_detail_data': entity_detail_data,
        }
        template = get_template( 'entity/panes/entity_details.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
            },
        )     

    
