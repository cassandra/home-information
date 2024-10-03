import logging

from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.views.generic import View

import hi.apps.common.antinode as antinode
from hi.apps.entity.models import Entity, EntityPosition
from hi.apps.location.forms import SvgPositionForm

from hi.constants import DIVID
from hi.decorators import edit_required
from hi.views import bad_request_response, page_not_found_response


logger = logging.getLogger(__name__)


@method_decorator( edit_required, name='dispatch' )
class EntityDetailsView( View ):

    def get( self, request, *args, **kwargs ):
        entity_id = kwargs.get( 'entity_id' )
        if not entity_id:
            return bad_request_response( request, message = 'Missing entity id in request.' )
        try:
            entity = Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            return page_not_found_response( request, message = f'No entity with id "{entity_id}".' )

        location_view = request.view_parameters.location_view

        svg_position_form = None
        if request.view_parameters.view_type.is_location_view:
            entity_position = EntityPosition.objects.filter(
                entity = entity,
                location = location_view.location,
            ).first()
            if entity_position:
                svg_position_form = SvgPositionForm.from_svg_position_model( entity_position )

        context = {
            'entity': entity,
            'svg_position_form': svg_position_form,
        }
        template = get_template( 'entity/edit/panes/entity_details.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['EDIT_ITEM']: content,
            },
        )     
