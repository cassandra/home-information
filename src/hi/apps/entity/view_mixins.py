from django.core.exceptions import BadRequest
from django.http import Http404, HttpRequest

import hi.apps.common.antinode as antinode
from hi.apps.entity.models import Entity
from hi.apps.entity.transient_models import EntityEditData


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
        # Entity editing now only happens in modal context
        # Sidebar in edit mode only shows read-only properties
        return antinode.modal_from_template(
            request = request,
            template_name = 'entity/modals/entity_edit.html',
            context = context,
        )
