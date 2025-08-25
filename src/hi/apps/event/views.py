from django.urls import reverse
from datetime import date, timedelta

from hi.apps.common.pagination import compute_pagination_from_queryset
from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView

from hi.hi_async_view import HiModalView

from .models import EventDefinition, EventHistory


class EventDefinitionsView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.EVENTS
    
    def get_main_template_name( self ) -> str:
        return 'event/panes/event_definitions.html'

    def get_main_template_context( self, request, *args, **kwargs ):
        event_definition_list = list(
            EventDefinition.objects.prefetch_related(
                'event_clauses',
                'event_clauses__entity_state',
                'alarm_actions',
                'control_actions',
            ).all().order_by('name')
        )
        return {
            'event_definition_list': event_definition_list,
        }


class EventHistoryView( HiModalView ):

    EVENT_HISTORY_PAGE_SIZE = 25

    def get_template_name( self ) -> str:
        return 'event/modals/event_history.html'
    
    def get( self, request, *args, **kwargs ):

        base_url = reverse( 'event_history' )

        queryset = EventHistory.objects.select_related(
            'event_definition'
        ).prefetch_related(
            'event_definition__event_clauses__entity_state__entity'
        ).all()
        pagination = compute_pagination_from_queryset( request = request,
                                                       queryset = queryset,
                                                       base_url = base_url,
                                                       page_size = self.EVENT_HISTORY_PAGE_SIZE,
                                                       async_urls = True )
        event_history_list = list(queryset[pagination.start_offset:pagination.end_offset + 1])

        for event_history in event_history_list:
            event_history.entity_count = event_history.event_definition.event_clauses.count()
            event_history.entity_names = [
                clause.entity_state.entity.name 
                for clause in event_history.event_definition.event_clauses.all()
            ]

        grouped_events = self._group_events_by_date(event_history_list)

        context = {
            'grouped_events': grouped_events,
            'pagination': pagination,
        }
        return self.modal_response( request, context )

    def _group_events_by_date(self, event_history_list):
        today = date.today()
        yesterday = today - timedelta(days=1)
        groups = {}

        for event_history in event_history_list:
            event_date = event_history.event_datetime.date()
            
            if event_date == today:
                date_label = "Today"
            elif event_date == yesterday:
                date_label = "Yesterday"
            else:
                date_label = event_date.strftime("%B %d, %Y")
            
            if date_label not in groups:
                groups[date_label] = []
            groups[date_label].append(event_history)

        return [{'date_label': label, 'events': events} for label, events in groups.items()]
