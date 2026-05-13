from django.core.exceptions import BadRequest
from django.http import Http404

from hi.apps.entity.models import Entity, EntityState


class EntityViewMixin:

    def get_entity( self, request, *args, **kwargs ) -> Entity:
        """ Assumes there is a required entity_id in kwargs """
        try:
            entity_id = int( kwargs.get( 'entity_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid item id.' )
        try:
            return Entity.objects.get( id = entity_id )
        except Entity.DoesNotExist:
            raise Http404( request )


class EntityStateViewMixin:

    def get_entity_state( self, request, *args, **kwargs ) -> EntityState:
        """ Assumes there is a required entity_state_id in kwargs """
        try:
            entity_state_id = int( kwargs.get( 'entity_state_id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid entity state id.' )
        try:
            return EntityState.objects.get( id = entity_state_id )
        except EntityState.DoesNotExist:
            raise Http404( request )
