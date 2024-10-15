import logging

from django.core.exceptions import BadRequest
from django.http import Http404

from hi.hi_async_view import HiSideView

from .entity_manager import EntityManager
from .models import Entity

logger = logging.getLogger(__name__)


class EntityDetailsView( HiSideView ):

    def get_template_name( self ) -> str:
        return 'entity/panes/entity_details.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        
        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            raise BadRequest( 'Missing entity id in request.' )
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404()

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = request.view_parameters.location_view

        entity_detail_data = EntityManager().get_entity_detail_data(
            entity = entity,
            current_location_view = current_location_view,
            is_editing = request.is_editing,
        )
        return {
            'entity_detail_data': entity_detail_data,
        }
