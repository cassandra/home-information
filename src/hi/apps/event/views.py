from django.urls import reverse

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

        queryset = EventHistory.objects.all()
        pagination = compute_pagination_from_queryset( request = request,
                                                       queryset = queryset,
                                                       base_url = base_url,
                                                       page_size = self.EVENT_HISTORY_PAGE_SIZE,
                                                       async_urls = True )
        event_history_list = queryset[pagination.start_offset:pagination.end_offset + 1]

        context = {
            'event_history_list': event_history_list,
            'pagination': pagination,
        }
        return self.modal_response( request, context )
