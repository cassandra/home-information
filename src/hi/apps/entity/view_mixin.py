from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest
from django.template.loader import get_template

import hi.apps.common.antinode as antinode
from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import EntityEditData

from hi.constants import DIVID


class EntityViewMixin:

    def get_entity( self, request, *args, **kwargs ) -> Entity:
        """ Assumes there is a required entity_id in kwargs """
        try:
            entity_id = int( kwargs.get( 'entity_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid entity id.' )
        try:
            return Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404( request )

    def entity_edit_response( self,
                              request           : HttpRequest,
                              entity_edit_data  : EntityEditData,
                              status_code       : int             = 200 ):

        context = entity_edit_data.to_template_context()
        template = get_template( 'entity/edit/panes/entity_edit.html' )
        content = template.render( context, request = request )
        return antinode.response(
            insert_map = {
                DIVID['ENTITY_EDIT_PANE']: content,
            },
            status = status_code,
        )
 
