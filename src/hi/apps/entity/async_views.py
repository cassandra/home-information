import logging

from hi.apps.location.location_manager import LocationManager

from hi.hi_async_view import HiSideView

from .entity_manager import EntityManager
from .view_mixin import EntityViewMixin

logger = logging.getLogger(__name__)


class EntityDetailsView( HiSideView, EntityViewMixin ):

    def get_template_name( self ) -> str:
        return 'entity/panes/entity_details.html'

    def should_push_url( self ):
        return True
    
    def get_template_context( self, request, *args, **kwargs ):
        entity = self.get_entity( request, *args, **kwargs )

        current_location_view = None
        if request.view_parameters.view_type.is_location_view:
            current_location_view = LocationManager().get_default_location_view( request = request )

        entity_details_data = EntityManager().get_entity_details_data(
            entity = entity,
            location_view = current_location_view,
            is_editing = request.is_editing,
        )
        return entity_details_data.to_template_context()
