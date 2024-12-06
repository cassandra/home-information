from hi.apps.config.enums import ConfigPageType
from hi.apps.config.views import ConfigPageView

from .models import EventDefinition


class EventDefinitionsView( ConfigPageView ):

    @property
    def config_page_type(self) -> ConfigPageType:
        return ConfigPageType.EVENTS
    
    def get_main_template_name( self ) -> str:
        return 'event/panes/event_definitions.html'

    def get_template_context( self, request, *args, **kwargs ):
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
