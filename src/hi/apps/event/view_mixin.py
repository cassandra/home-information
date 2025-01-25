from django.core.exceptions import BadRequest
from django.http import Http404

from .models import EventDefinition


class EventViewMixin:

    EVENT_CLAUSE_FORMSET_PREFIX = 'event-clause'
    ALARM_ACTION_FORMSET_PREFIX = 'alarm-action'
    CONTROL_ACTION_FORMSET_PREFIX = 'control-action'
    
    def get_event_definition( self, request, *args, **kwargs ) -> EventDefinition:
        """ Assumes there is a required "id" in kwargs """
        try:
            event_definition_id = int( kwargs.get( 'id' ))
        except (TypeError, ValueError):
            raise BadRequest( 'Invalid event definition id.' )
        try:
            return EventDefinition.objects.prefetch_related(
                'event_clauses',
                'event_clauses__entity_state',
                'alarm_actions',
                'control_actions',
            ).get( id = event_definition_id )
        except EventDefinition.DoesNotExist:
            raise Http404( request )

